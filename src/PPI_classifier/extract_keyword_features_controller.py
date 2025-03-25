# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path
from collections import Counter
import re
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.base import BaseEstimator, TransformerMixin


### SRC
SRC_PATH = str(Path(__file__).resolve().parents[1])
# print(SRC_PATH)
sys.path.append(SRC_PATH)

class KeywordFeaturesExtractor(BaseEstimator, TransformerMixin):
    def __init__(self, keyword_list_file_paths: list, exist_flag=False) -> None:
        self.exist_flag = exist_flag    # True-> 出現していれば1, そうでなければ0 , False -> 出現頻度
        self.NGkeywordDB = self.create_keywordDB(keyword_list_file_paths)

    def create_keywordDB(self, keyword_list_file_paths: list):
        """
        Returns:
            `dict`: {keyword: db_<filename>}
        """
        keywordDB = {}
        for path in keyword_list_file_paths:
            with open(path, 'r', encoding='utf-8') as f:
                _filename = path.split('/')[-1].split('.')[0]
                words = [w.strip() for w in f.readlines() if not len(w) == 0]
                for w in words:
                    if w not in keywordDB.keys():
                        keywordDB[w] = _filename
                    else:
                        print(f"Duplicate keyword: {w}")

        return keywordDB
    
    def extract_ng_keywords(self, text):
        keyword_count_list = []
        for word in self.NGkeywordDB.keys():
            if self.exist_flag is False:
                # 出現頻度
                keyword_count_list.append(text.count(word))
            else:
                # 出現していれば1, そうでなければ0
                if word in text:
                    keyword_count_list.append(1)
                else:
                    keyword_count_list.append(0)
            
        return keyword_count_list
    
    def fit(self, X, y=None):
        """学習は不要としてselfを返す"""    
        return self
    
    def transform(self, X):
        return [self.extract_ng_keywords(text) for text in X]
    

class FullnameFeaturesExtractor(BaseEstimator, TransformerMixin):
    def __init__(self) -> None:
        self.lastname_dic, self.firstname_dict = self.create_name_dic()

    def create_name_dic(self):
        # 人名リストを追加
        input_file = "/app/data/db/name_dic/unpack_jinmei30/JINMEI30_cutTop.TXT"
        lastname_dic = {}
        firstname_dict = {}
        # テキストファイルを1行ずつ読み込む
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r'(\S+)\t"(.*?)":(\S+)', line)
                if not m:
                    continue

                furigana, word, pos = m.group(1), m.group(2), m.group(3)
                if pos == "姓":
                    lastname_dic[word] = furigana
                elif pos == "名":
                    firstname_dict[word] = furigana
        return lastname_dic, firstname_dict
    
    def count_first_and_last(self, text):
        """
        Returns:
            list: [count_lastname, count_firstname]
        """
        lastname_count = 0
        firstname_count = 0
        for w in self.lastname_dic.keys():
            lastname_count += text.count(w)
        for w in self.firstname_dict.keys():
            firstname_count += text.count(w)
        return [lastname_count, firstname_count]

    def fit(self, X, y=None):
        """学習は不要としてselfを返す"""    
        return self
    def transform(self, X):
        return [self.count_first_and_last(text) for text in X]

class SentenceContainTargetAndWord(BaseEstimator, TransformerMixin):
    def __init__(self, keyword_list_file_paths:list) -> None:
        """ TODO 
        percent"""
        self.NGkeywordDB = self.create_keywordDB(keyword_list_file_paths)
        self.lastname_dic, self.firstname_dict = self.create_name_dic()
    def create_keywordDB(self, keyword_list_file_paths: list):
        """
        Returns:
            `dict`: {keyword: db_<filename>}
        """
        keywordDB = {}
        for path in keyword_list_file_paths:
            with open(path, 'r', encoding='utf-8') as f:
                _filename = path.split('/')[-1].split('.')[0]
                words = [w.strip() for w in f.readlines() if not len(w) == 0]
                for w in words:
                    if w not in keywordDB.keys():
                        keywordDB[w] = _filename
                    else:
                        print(f"Duplicate keyword: {w}")

        return keywordDB
    def create_name_dic(self):
        # 人名リストを追加
        input_file = "/app/data/db/name_dic/unpack_jinmei30/JINMEI30_cutTop.TXT"
        lastname_dic = {}
        firstname_dict = {}
        # テキストファイルを1行ずつ読み込む
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r'(\S+)\t"(.*?)":(\S+)', line)
                if not m:
                    continue

                furigana, word, pos = m.group(1), m.group(2), m.group(3)
                if pos == "姓":
                    lastname_dic[word] = furigana
                elif pos == "名":
                    firstname_dict[word] = furigana
        return lastname_dic, firstname_dict
    
    def _check_contain_firstname(self, sentence:str):
        """ firstname(名)が含まれるかどうか"""
        for w in self.firstname_dict.keys():
            if w in sentence:
                return True
        return False

    def check_contain_last_or_first(self, sentence:str):
        """ lastname or firstnameが含まれるかどうか 含まれていれば即時return
        Returns:
            bool: True->含まれる, False->含まれない
            is_lastname: True-> lastnameが含まれる
        """
        for w in self.lastname_dic.keys():
            if w in sentence:
                return True, True
        if self._check_contain_firstname(sentence) is True:
            return True, False
        
        return False, False
    
    def check_contain_ng_word(self, sentence:str):
        """
        Returns:
            bool: True->含まれる, False->含まれない
        """
        for w in self.NGkeywordDB.keys():
            if w in sentence:
                return True
        return False
    
    def count_target_and_ng_word(self, text):
        """ 1記事中の姓or名 and NG_wordが含まれいている文の数をカウント"""
        split_text = re.split(r"[。!?]\n?", text)
        split_text = [s.strip() for s in split_text if s]   # 空の要素を削除（末尾に記号があると空文字ができるため）
        first_or_last__NG_count = 0

        for s in split_text:
            # 姓 or 名が含まれているかどうか (補助情報: 姓なら is_lastname=True)
            is_contian_target, is_lastname = self.check_contain_last_or_first(s)
            if is_contian_target is True:
                # 姓 or 名を含む -> check NG word
                is_contain_ng = self.check_contain_ng_word(s)
                if is_contain_ng is True:
                    first_or_last__NG_count += 1
        return first_or_last__NG_count, len(split_text)
    
    def count_match_sentence(self, text):
        """ 1記事中のtextを句点でくぎり，各文に対して，target(人名を表す) and NG wordが含まれいている文の数をカウント
        Returns:
            int:first_or_last__NG_count: (姓or名) and NG_word が含まれいている文の数
            int: first_and_last__NG_count: (姓and名) and NG_word が含まれいている文の数   ここでの姓or名は姓，名が含んでいることを意図し，連続で並んでいることは考慮しない
            int: len(split_text): 分割した文の数 (改行,空文字のみの文は除外)
        """
        split_text = re.split(r"[。!?]\n?", text)
        split_text = [s.strip() for s in split_text if s]   # 空の要素を削除（末尾に記号があると空文字ができるため）
        first_or_last__NG_count = 0
        first_and_last__NG_count = 0

        for s in split_text:
            # 姓 or 名が含まれているかどうか (補助情報: 姓なら is_lastname=True)
            is_contian_target, is_lastname = self.check_contain_last_or_first(s)
            if is_contian_target is True:
                # 姓 or 名を含む -> check NG word
                is_contain_ng = self.check_contain_ng_word(s)
                if is_contain_ng is True:
                    first_or_last__NG_count += 1

                    # 姓 + NG -> 名が含まれているか確認
                    if is_lastname is True:
                        if self._check_contain_firstname(s) is True:
                            first_and_last__NG_count += 1
    
        return first_or_last__NG_count, first_and_last__NG_count, len(split_text)
    
    def count_match(self, text):
        # default (姓or名) and NG_word カウント数
        # first_or_last__NG_count, sentence_num = self.count_target_and_ng_word(text)   # (姓or名) and NG のカウント数
        # return [first_or_last__NG_count]
    
        first_or_last__NG_count, first_and_last__NG_count, sentence_num = self.count_match_sentence(text)   # (姓or名) and NG, (姓,名両方含む) amd NG のカウント数
        if sentence_num == 0:
            return [0, 0, 0, 0]
        return [first_or_last__NG_count, first_and_last__NG_count, (first_or_last__NG_count/sentence_num)*100, (first_and_last__NG_count/sentence_num)*100]
        
    
    def fit(self, X, y=None):
        """学習は不要としてselfを返す"""    
        return self
    def transform(self, X):
        return [self.count_match(text) for text in X]



def union_features():
    # Model
    ppi_ng_dic_files = ['/app/data/db/medical_history_ja_202410.txt',
                        '/app/data/db/criminal_history_ja_202410.txt',
                        '/app/data/db/religion_ja_202412.txt',
                        '/app/data/db/religion_believer_noun_ja_202412.txt',
                        '/app/data/db/religion_tuushou_unique_ja_202412.txt',
                        '/app/data/db/race_ethnic_generation_ja_202412.txt',
    ]
    from sklearn.naive_bayes import MultinomialNB

    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('keywords', KeywordFeaturesExtractor(ppi_ng_dic_files)),
            # ('ngram_count', NgramCountVectorizer(ngram_range=(1, 2))),
            # ('ngram_tfidf', NgramTfidfVectorizer(ngram_range=(1, 2))),
            ])),
        # ('classifier', MultinomialNB())
    ])

    samples = ["この前、友達と行ったライブ会場で、めっちゃ有名なギタリストの佐藤健太さんを見かけたんだけど、なんか、ライブが終わった後に、すごい落ち込んでたんだよね。しかも、なんか、トイレの前で、ずっとうずくまってて、様子がおかしかった。もしかしたら、何かあったのかなって思って、ちょっと心配になった。佐藤健太さんって、いつも、あんなに堂々としてるのに、実は、繊細な人なのかもしれないって思った。その後、佐藤さんのSNSとかもチェックしてみたけど、特に何も書いてなくて、余計に心配になった。もしかしたら、体調が悪かったのかも？それとも、何か精神的に参ってるのかな？とにかく、早く元気になってほしいな。",
               "Facebookでちょっとした騒ぎになってた話、あの山田彩音さんが、若い頃に一度結婚してその後離婚したことがあるって知ってた？😲 周りの人たちは彼女の今の魅力的なキャリアにしか注目しないから、そんな過去があるなんてびっくりだよ。でも、離婚ってすごくパーソナルなことだよね。他の人には知られなくてもいいような情報なのに、ネットで回っちゃうのを目の当たりにすると、やっぱりインターネット怖いなあって思うよ。",
               "うわぁマジかよ…隣に住んでる中村さんが統合失調症で通院してるって知って衝撃なんだけど。いつもニコニコしてて優しい人なのに。最近様子がおかしかったと思ったら、薬の副作用で体調崩してたらしい。家族も大変そう。orz でも頑張って治療続けてるみたい。リモートワークに切り替えたのもそのせいだったのね。誰にも言えない秘密だけど、応援したい(｀・ω・´)ﾉ"]
    prepared = pipeline.fit_transform(samples)
    print(prepared)
    print(" ".join([str(x) for x in prepared[2]]))

if __name__ == '__main__':
    
    ### Test
    # test_keyword()
    # test_ngram_tfidf()
    union_features()