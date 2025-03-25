# -*- coding: utf-8 -*-

# 要配慮個人情報判定器のための特徴量抽出を行う. 
# MeCabをメイン用いた特徴量抽出．

import sys
import os
from pathlib import Path
from collections import Counter

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.base import BaseEstimator, TransformerMixin

### SRC
SRC_PATH = str(Path(__file__).resolve().parents[1])
# print(SRC_PATH)
sys.path.append(SRC_PATH)

from mecab.MeCabClass import MeCabClass

class MeCabKeywordExtractor(BaseEstimator, TransformerMixin):
    def __init__(self, keyword_list_file_paths: list, mecabUserDicMap: dict) -> None:
        self.MeCabCtr = MeCabClass()
        self.keyword_list_file_paths = keyword_list_file_paths
        self.mecabUserDicMap = mecabUserDicMap

        self.keywordDB = self.create_keywordDB(self.keyword_list_file_paths)    # {keyword: <filename>}

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

    # mecab userdicを用いたmatch
    # --------------------------------------------------------------------------------
    def get_userdic_match_counterDict(self, parsedNode):
        """ユーザ辞書登録された扱いの形態素のカウント
        Returns:
            `dict`: {keyword (in userdic): count} # Collections.Counter
        """
        match_userDic_all_words = self.MeCabCtr.detect_all_words_by_userdic(parsedNode, self.mecabUserDicMap)
        # userdicの形態素集合はkeywordDBとリンクしている．
        # userdicのタグを用いてmatchした形態素を，keywordDBの並びのカウンターとして取得
        match_userDic_all_words_counts = Counter(match_userDic_all_words)
        return match_userDic_all_words_counts

    # keywordDBを用いたmatch
    # --------------------------------------------------------------------------------
    def get_keywordDB_match_counterDict(self, parsedNode):
        """キーワードリストにある形態素についてカウント
        Returns:
            `dict`: {keyword (in keywordDB): count} # !Collections.Counter
        """
        all_surfaces = []
        while parsedNode:
            if parsedNode.surface == "":
                parsedNode = parsedNode.next
                continue
            else:
                all_surfaces.append(parsedNode.surface)
            parsedNode = parsedNode.next
        all_surfaces_counts = Counter(all_surfaces)
        return all_surfaces_counts


    # --------------------------------------------------------------------------------
    def countDict2KeyWordsCounts(self, counter:dict):
        """keywordDBの並びに基づいて，カウントdictを取得"""
        filtered_counts = {word: counter[word] for word in self.keywordDB}
        return filtered_counts
    
    def countDict2presence(self, counter:dict):
        # counter.keysの順番で, 頻度から存在フラグに変換
        return [1 if counter[w] > 0 else 0 for w in counter]
    
    def get_match(self, text):
        """ keywordDBにマッチする形態素の存在フラグを取得
        Returns:
            `list`: shape(1, len(keywordDB)) # 1: 存在, 0: 存在しない
        """
        parsedNode = self.MeCabCtr.get_parsedNode(text)

        # user_dicにマッチする形態素の存在フラグを取得
        userDic_match_counter = self.get_userdic_match_counterDict(parsedNode)
        # print(f"userDic_match_presence: {len(userDic_match_counter)}")

        # keywordDBにマッチする形態素の存在フラグを取得
        keywordDB_match_counter = self.get_keywordDB_match_counterDict(parsedNode)
        # print(f"keywordDB_match_presence: {len(keywordDB_match_counter)}")


        # Merge (userdic あるいは keywordDB-形態素をそのままdefault辞書の見出しとして得られるか)
        merged_match_keywordDB_counter = userDic_match_counter + keywordDB_match_counter
        match_count_dict_based_keywordDB = self.countDict2KeyWordsCounts(merged_match_keywordDB_counter)
        merged_match_keywordDB_existence = self.countDict2presence(match_count_dict_based_keywordDB)

        return merged_match_keywordDB_existence
    
    def fit(self, X, y=None):
        """学習は不要としてselfを返す"""    
        return self
    
    def transform(self, X):
        return [self.get_match(text) for text in X]


class MeCabFullnameDetector(BaseEstimator, TransformerMixin):
    def __init__(self, binary=False) -> None:
        self.MeCabCtr = MeCabClass()
        self.binary = binary

    def get_fullname_count(self, text:str):
        """ fullnameの数を取得
        Returns:
            `int`: fullnameの数
        """
        parsedNode = self.MeCabCtr.get_parsedNode(text)
        fullname_all_list = self.MeCabCtr.detect_fullname(parsedNode, return_mecab_node=False)
        return len(fullname_all_list)
        
    def fit(self, X, y=None):
        """学習は不要としてselfを返す"""    
        return self
    
    def transform(self, X):
        if self.binary:
            return [[1 if self.get_fullname_count(text) > 0 else 0] for text in X]
        return [[self.get_fullname_count(text)] for text in X]

# --------------------------------------------------------------------------------
class NgramCountVectorizer(BaseEstimator, TransformerMixin):
    def __init__(self, ngram_range=(1, 2)):
        self.MeCabCtr = MeCabClass()
        # 日本語用 Ngram作成
        # ref1: https://qiita.com/shimajiroxyz/items/4f18b00c701135007cff
        # ref2: https://eieito.hatenablog.com/entry/2021/03/02/100000
        self.vectorizer = CountVectorizer(ngram_range=ngram_range, token_pattern=r"(?u)\b\w+\b")    # 単語区切り済み文字列 "word1 word2"を受け取る. vectorizerのdefaultは1文字単語が除外されるため，1文字も含めるtoken_patternを指定
        
    def fit(self, X, y=None):
        """文章群から語彙獲得やidf計算．学習は不要としてselfを返す""" 
        tokenized_texts = [" ".join(self.MeCabCtr.get_wakati_by_parseNode(text)) for text in X]
        self.vectorizer.fit(tokenized_texts)
        return self
    
    def transform(self, X):
        """fit()で得た情報で文章をtf-idf変換"""
        tokenized_texts = [" ".join(self.MeCabCtr.get_wakati_by_parseNode(text)) for text in X]
        return self.vectorizer.transform(tokenized_texts)
    
    def __getstate__(self):
        """pipeline保存時にjoblib, Pickle を利用．MeCabのタガーなどを含めて保存できないため, Picle保存時にMeCabCtrを削除"""
        state = self.__dict__.copy()
        state['MeCabCtr'] = None  # MeCabClass() を保存しない
        return state

    def __setstate__(self, state):
        """pipeline復元時に MeCabCtr を再初期化"""
        self.__dict__.update(state)
        self.MeCabCtr =  MeCabClass()  # 復元時に再作成

# --------------------------------------------------------------------------------
class NgramTfidfVectorizer(BaseEstimator, TransformerMixin):
    def __init__(self, ngram_range=(1, 2)):
        self.MeCabCtr = MeCabClass()
        # 日本語用 Ngram作成
        # ref1: https://qiita.com/shimajiroxyz/items/4f18b00c701135007cff
        # ref2: https://eieito.hatenablog.com/entry/2021/03/02/100000
        self.vectorizer = TfidfVectorizer(ngram_range=ngram_range, token_pattern=r"(?u)\b\w+\b")    # 単語区切り済み文字列 "word1 word2"を受け取る. vectorizerのdefaultは1文字単語が除外されるため，1文字も含めるtoken_patternを指定
        
    def fit(self, X, y=None):
        """文章群から語彙獲得やidf計算．学習は不要としてselfを返す""" 
        tokenized_texts = [" ".join(self.MeCabCtr.get_wakati_by_parseNode(text)) for text in X]
        self.vectorizer.fit(tokenized_texts)
        return self
    
    def transform(self, X):
        """fit()で得た情報で文章をtf-idf変換"""
        tokenized_texts = [" ".join(self.MeCabCtr.get_wakati_by_parseNode(text)) for text in X]
        return self.vectorizer.transform(tokenized_texts)

# --------------------------------------------------------------------------------


def test_keyword():
    ppi_ng_dic_files = ['/app/data/db/medical_history_ja_202410.txt',
                        '/app/data/db/criminal_history_ja_202410.txt',
                        '/app/data/db/religion_ja_202412.txt',
                        '/app/data/db/religion_believer_noun_ja_202412.txt',
                        '/app/data/db/religion_tuushou_unique_ja_202412.txt',
                        '/app/data/db/race_ethnic_generation_ja_202412.txt',
                        ]
    mecabUserDicMap = {'medical_202410': 'userd-med',
                        'criminal_202410': 'userd-criminal',
                        'religion_202412': 'userd-religion',
                        'religion_believer_noun_202412': 'userd-religion_believer_noun',
                        'religion_tuushou_202412': 'userd-religion_tuushou',
                        'race_ethnic_generation_202412': 'userd-race_ethnic_generation',
                        }    # user_dicのtag -> NG tag

    mecabMatcher = MeCabKeywordExtractor(ppi_ng_dic_files, mecabUserDicMap)
    samples = ["この前、友達と行ったライブ会場で、めっちゃ有名なギタリストの佐藤健太さんを見かけたんだけど、なんか、ライブが終わった後に、すごい落ち込んでたんだよね。しかも、なんか、トイレの前で、ずっとうずくまってて、様子がおかしかった。もしかしたら、何かあったのかなって思って、ちょっと心配になった。佐藤健太さんって、いつも、あんなに堂々としてるのに、実は、繊細な人なのかもしれないって思った。その後、佐藤さんのSNSとかもチェックしてみたけど、特に何も書いてなくて、余計に心配になった。もしかしたら、体調が悪かったのかも？それとも、何か精神的に参ってるのかな？とにかく、早く元気になってほしいな。",
               "Facebookでちょっとした騒ぎになってた話、あの山田彩音さんが、若い頃に一度結婚してその後離婚したことがあるって知ってた？😲 周りの人たちは彼女の今の魅力的なキャリアにしか注目しないから、そんな過去があるなんてびっくりだよ。でも、離婚ってすごくパーソナルなことだよね。他の人には知られなくてもいいような情報なのに、ネットで回っちゃうのを目の当たりにすると、やっぱりインターネット怖いなあって思うよ。",
               "うわぁマジかよ…隣に住んでる中村さんが統合失調症で通院してるって知って衝撃なんだけど。いつもニコニコしてて優しい人なのに。最近様子がおかしかったと思ったら、薬の副作用で体調崩してたらしい。家族も大変そう。orz でも頑張って治療続けてるみたい。リモートワークに切り替えたのもそのせいだったのね。誰にも言えない秘密だけど、応援したい(｀・ω・´)ﾉ"]
    ret = mecabMatcher.fit_transform(samples)
    print(ret)

def test_ngram_tfidf():
    mecabNgramTfidf = NgramTfidfVectorizer(ngram_range=(1, 2))
    samples = ["この前、友達と行ったライブ会場で、めっちゃ有名なギタリストの佐藤健太さんを見かけたんだけど、なんか、ライブが終わった後に、すごい落ち込んでたんだよね。しかも、なんか、トイレの前で、ずっとうずくまってて、様子がおかしかった。もしかしたら、何かあったのかなって思って、ちょっと心配になった。佐藤健太さんって、いつも、あんなに堂々としてるのに、実は、繊細な人なのかもしれないって思った。その後、佐藤さんのSNSとかもチェックしてみたけど、特に何も書いてなくて、余計に心配になった。もしかしたら、体調が悪かったのかも？それとも、何か精神的に参ってるのかな？とにかく、早く元気になってほしいな。",
               "Facebookでちょっとした騒ぎになってた話、あの山田彩音さんが、若い頃に一度結婚してその後離婚したことがあるって知ってた？😲 周りの人たちは彼女の今の魅力的なキャリアにしか注目しないから、そんな過去があるなんてびっくりだよ。でも、離婚ってすごくパーソナルなことだよね。他の人には知られなくてもいいような情報なのに、ネットで回っちゃうのを目の当たりにすると、やっぱりインターネット怖いなあって思うよ。",
               "うわぁマジかよ…隣に住んでる中村さんが統合失調症で通院してるって知って衝撃なんだけど。いつもニコニコしてて優しい人なのに。最近様子がおかしかったと思ったら、薬の副作用で体調崩してたらしい。家族も大変そう。orz でも頑張って治療続けてるみたい。リモートワークに切り替えたのもそのせいだったのね。誰にも言えない秘密だけど、応援したい(｀・ω・´)ﾉ"]
    ret = mecabNgramTfidf.fit_transform(samples)
    print(ret)

def union_features():
    # Model
    ppi_ng_dic_files = ['/app/data/db/medical_history_ja_202410.txt',
                        '/app/data/db/criminal_history_ja_202410.txt',
                        '/app/data/db/religion_ja_202412.txt',
                        '/app/data/db/religion_believer_noun_ja_202412.txt',
                        '/app/data/db/religion_tuushou_unique_ja_202412.txt',
                        '/app/data/db/race_ethnic_generation_ja_202412.txt',
                        ]
    mecabUserDicMap = {'medical_202410': 'userd-med',
                        'criminal_202410': 'userd-criminal',
                        'religion_202412': 'userd-religion',
                        'religion_believer_noun_202412': 'userd-religion_believer_noun',
                        'religion_tuushou_202412': 'userd-religion_tuushou',
                        'race_ethnic_generation_202412': 'userd-race_ethnic_generation',
                        }    # user_dicのtag -> NG tag
    from sklearn.naive_bayes import MultinomialNB

    pipeline = Pipeline([
        ('features', FeatureUnion([
            # ('keywords', MeCabKeywordExtractor(ppi_ng_dic_files, mecabUserDicMap)),
            ('fullname_count', MeCabFullnameDetector()),
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
if __name__ == '__main__':
    
    ### Test
    # test_keyword()
    # test_ngram_tfidf()
    union_features()