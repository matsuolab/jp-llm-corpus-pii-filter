# -*- coding: utf-8 -*-

# Mecabを用いたRule-based PPI判定フィルタ

import sys
import os
from pathlib import Path
import re

import hojichar
from hojichar import document_filters, Document

### SRC
SRC_PATH = str(Path(__file__).resolve().parents[1])
sys.path.append(SRC_PATH)

from mecab.MeCabClass import MeCabClass

class ProtectPersonalInformationJa_v1(hojichar.core.filter_interface.Filter):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mecab = MeCabClass()

        ### NG words
        ng_key_dic_file_paths = ['/app/data/db/medical_history_ja_202410.txt',
                                 '/app/data/db/criminal_history_ja_202410.txt',
                                 '/app/data/db/religion_ja_202412.txt',
                                 '/app/data/db/religion_believer_noun_ja_202412.txt',
                                 '/app/data/db/religion_tuushou_unique_ja_202412.txt',
                                 '/app/data/db/race_ethnic_generation_ja_202412.txt',
                                 ]
        



        ### NG words for regex
        # self.ng_criminal_pat = self.create_NgWords_regex(self.ng_criminal_dict_path)
        # self.ng_medical_pat = self.create_NgWords_regex(ng_medical_dict_path)

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


    # Detect NgWords
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


    def create_NgWords_regex(self, words_path: str):
        """NgWordsの正規表現pattern(compiled)を作成
        """
        with open(words_path, 'r', encoding='utf-8') as f:
            ng_words = f.readlines()
            ng_words = [w.strip() for w in ng_words if not len(w) == 0]
            
            pat = '|'.join(ng_words)
            return re.compile(pat)
        
    def detect_NgWords_regex(self, doc: Document) -> tuple:
        """正規表現を用いたNgWords検出
        - 利用ワードリスト: 病名(med), 
        """
        # 病名
        med_match = self.ng_medical_pat.search(doc.text)
        if med_match:
            return True, "med"
        
        return False, None


    # Detect PPI
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



    def is_PPI_using_regexNgWords(self, doc: Document) -> tuple:
        """
        - [Algorithm] fullname, NgWords判定をそれぞれ実行
        - NG words判定: 
        - fullname判定: MeCab user辞書
        Returns:
            reject_flag bool: PPIが含まれるので破棄対象かどうか
            fullnames list(str): 抽出したfullnameリスト
            ng_type str: NgWordsの種類
        """  
        ### fullname ->  NgWords(regex)
        # [MeCab] parse結果を取得し，filter判定に用いる
        parsedNode = self.mecab.get_parsedNode(doc.text)
        fullnames = self.mecab.detect_fullname(parsedNode, return_mecab_node=False, debug=False)
        
        # [NgWords] 
        is_detect_NgWords, ng_type = self.detect_NgWords_regex(doc)


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
    

    def apply(self, doc: Document) -> Document:
        """要配慮個人情報として，fullnameが存在し，かつ NGワードが存在する記事は破棄
        TODO: metadata:情報記載
        """
        # reject_flag, fullnames, ng_type = self.is_PPI_using_regexNgWords(doc)    # 正規表現NgWords判定
        # reject_flag, fullnames, ng_type = self.is_PPI_using_userdicNgWords(doc)    # MeCab user dicを用いたNgWords判定
        reject_flag, fullnames, ng_match = self.is_PPI3(doc)    # MeCab userdic & default dicを用いたNgWords判定

        if reject_flag is True:
            doc.is_rejected = True
        
        doc.metadata['detect_fullnames'] = fullnames
        doc.metadata['ng_match'] = ng_match

        return doc
    
    
    
