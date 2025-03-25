# -*- coding: utf-8 -*-

# Mecabを用いたRule-based PPI判定フィルタ(custom_document_filter_PPI.py) と 
# PPI判定分類器(custom_document_filter_PPI_classifier.py) を組み合わせたフィルタリングを行う

import sys
import os
from pathlib import Path
import re
import pickle

import hojichar
from hojichar import document_filters, Document

### PROJ
PROJ_PATH = str(Path(__file__).resolve().parents[2])
sys.path.append(PROJ_PATH)

from src.mecab.MeCabClass import MeCabClass
from src.PPI_classifier.ppi_NB_classifier_inference import PPI_NaiveBaysianClassifier

class ProtectPersonalInformationRulebaseAndClassifier(hojichar.core.filter_interface.Filter):
    def __init__(self, add_ppi_info:bool, *args, **kwargs) -> None:
        """
        Args:
            add_ppi_info: bool debug用にPPI判定情報をmetadataに追加するかどうか DocumentをDetailDocuemnt classを利用して読み込むこと
        """
        super().__init__(*args, **kwargs)
        self.add_ppi_info = add_ppi_info

        # ----- Rule-based filter ------------------------------------------------------------------------
        self.mecab = MeCabClass()   # Rule-based filterのためのmecabインスタンス

        ### NG words user辞書判定されなかったときに，形態素として一致していればNGとする
        ng_key_dic_file_paths = ['/app/data/db/medical_history_ja_202410.txt',
                                 '/app/data/db/criminal_history_ja_202410.txt',
                                 '/app/data/db/religion_ja_202412.txt',
                                 '/app/data/db/religion_believer_noun_ja_202412.txt',
                                 '/app/data/db/religion_tuushou_unique_ja_202412.txt',
                                 '/app/data/db/race_ethnic_generation_ja_202412.txt',
                                 ]

        ### MeCab NG words
        self.mecabUserDicTag2NgTag = {'medical_202410': 'userd-med',
                                      'criminal_202410': 'userd-criminal',
                                      'religion_202412': 'userd-religion',
                                      'religion_believer_noun_202412': 'userd-religion_believer_noun',
                                      'religion_tuushou_202412': 'userd-religion_tuushou',
                                      'race_ethnic_generation_202412': 'userd-race_ethnic_generation',
                                      }    # user_dicのtag -> NG tag

        ### NG words set
        self.ng_words_db = self.create_NgWords_db(ng_key_dic_file_paths)
        # print(f"NgWords DB: {len(self.ng_words_db.keys())}"); exit()

        # ----- Classifier filter ------------------------------------------------------------------------
        self.PPI_NB_classifier = PPI_NaiveBaysianClassifier()
        # Load trained pipeline
        trained_pipeline_path = PROJ_PATH + '/src/PPI_classifier/models/NB_pipeline_202503.pkl'
        with open(trained_pipeline_path, 'rb') as f:
            trained_pipeline = pickle.load(f)
            print(f'loaded trained_pipeline: {trained_pipeline_path=}, type={type(trained_pipeline)}')
        self.PPI_NB_classifier.set_pipeline(trained_pipeline)


    # [Rule-based] Detect NgWords
    # -------------------------------------------------------------------------------------
    def create_NgWords_db(self, ng_key_dic_file_paths: list):
        """
        Returns:
            `dict`: {ng_word: db_<filename>}
        """
        ng_words_db = {}
        for path in ng_key_dic_file_paths:
            with open(path, 'r', encoding='utf-8') as f:
                _filename = path.split('/')[-1].split('.')[0]
                ng_words = f.readlines()
                ng_words = [w.strip() for w in ng_words if not len(w) == 0]
                
                for w in ng_words:
                    if w not in ng_words_db.keys():
                        ng_words_db[w] = _filename
                    else:
                        continue

        return ng_words_db


    # [Rule-based] Detect PPI
    # -------------------------------------------------------------------------------------
    def is_PPI_using_userdicNgWords(self, doc: Document) -> tuple:
        """ 
        - [Algorithm] fullname, NgWords判定をそれぞれ実行
        - NG words判定: MeCab user辞書を利用        
        - fullname判定: MeCab user辞書
        """
        ### fullname ->  NgWords(regex)
        # [MeCab] parse結果を取得し，filter判定に用いる. parse結果は再利用想定
        parsedNode = self.mecab.get_parsedNode(doc.text)
        fullnames = self.mecab.detect_fullname(parsedNode)

        # [NgWords]
        # use user_dic
        is_detect_NgWords, ng_type = self.mecab.detect_NgWords_by_userdic(parsedNode, self.mecabUserDicTag2NgTag)
        

        # 判定
        if len(fullnames) > 0 and is_detect_NgWords:
            return True, fullnames, ng_type

        return False, fullnames, None


    def is_PPI3(self, doc: Document) -> tuple:
        """ 
        - [Algorithm] 以下の判定をそれぞれ実行
        - fullname判定: MeCab user辞書
        - NG words判定: MeCab user辞書を利用        
        - NG words判定: MeCab default辞書とNG wordsリストとのMatching
        """
        ### fullname ->  NgWords(regex)
        # [MeCab] parse結果を取得し，filter判定に用いる. parse結果は再利用想定
        parsedNode = self.mecab.get_parsedNode(doc.text)
        fullnames = self.mecab.detect_fullname(parsedNode)

        # [NgWords]
        # use user_dic
        is_detect_NgWords_userdic, ng_type = self.mecab.detect_NgWords_by_userdic(parsedNode, self.mecabUserDicTag2NgTag)
        # use wordDB
        is_detect_NgWords_defaultdic, ng_word, ng_db_filename = self.mecab.detect_NgWords_by_wordDB(parsedNode, self.ng_words_db)


        # 判定
        ng_match = []
        if len(fullnames) > 0 and (is_detect_NgWords_userdic or is_detect_NgWords_defaultdic):
            if is_detect_NgWords_userdic:
                ng_match.append(ng_type)
            if is_detect_NgWords_defaultdic:
                ng_match.append(ng_db_filename)

            return True, fullnames, ng_match

        return False, fullnames, None
    

    # [classifier] Detect PPI
    # -------------------------------------------------------------------------------------
    def predict_PPI_by_classifier(self, doc: Document) -> bool:
        text = doc.text
        y_pred = self.PPI_NB_classifier.pipeline.predict([text])

        if int(y_pred[0]) == 1:
            # 要配慮個人情報に該当
            return True
        else:
            return False
        
    def apply(self, doc: Document) -> Document:
        """要配慮個人情報であるかの判定を以下の2点を満たすかで判定する．
        - 1. fullnameが存在し，かつ NGワードが存在する
        - 2. PPI判定機械学習分類器による判定
        
        Returns:
            doc: Document
                doc.is_rejected: bool True: 要配慮個人情報を含む記事, False: 含まない記事
                doc.metadata['detect_fullnames']: list(str)
                doc.metadata['ng_match']: list(str)
                doc.metadata['is_PPI_by_classifier']: int
        """
        # Rule-based filter
        reject_flag, fullnames, ng_match = self.is_PPI3(doc)    # MeCab userdic & default dicを用いたNgWords判定
        
        is_PPI_by_classifier = False
        if reject_flag is True:
            # PPI classifier
            is_PPI_by_classifier = self.predict_PPI_by_classifier(doc)
            if is_PPI_by_classifier is True:
                doc.is_rejected = True
        
        # Add metadata
        if self.add_ppi_info is True:
            doc.metadata['detect_fullnames'] = fullnames
            doc.metadata['ng_match'] = ng_match
            doc.metadata['is_PPI_by_classifier'] = 1 if is_PPI_by_classifier is True else 0

        return doc
    
    
    
