# -*- coding: utf-8 -*-
# MeCab(mecab-python3)
import os
import MeCab

class MeCabClass(object):
    def __init__(self):
        self.tagger = MeCab.Tagger()  # Ubuntu: /usr/local/etc/mecabrc の設定を読み込む

        # dic指定
        # dict_dir = '/var/lib/mecab/dic/juman-utf8'  # mecab install時default辞書
        # dict_dir = os.path.dirname(os.path.abspath(__file__)) + '/unidic-cwj-202302_full'
        # print(f'use dict_dir: {dict_dir}')
        # self.tagger = MeCab.Tagger(f'-d {dict_dir}')

        # self.tagger = MeCab.Tagger('-u /app/src/mecab/mecab_userdic/dic/ipa_jinmei_v3.dic')
        user_dic_paths = ['/app/src/mecab/mecab_userdic/dic/ipa_jinmei_v3.dic',     # 人名
                          '/app/src/mecab/mecab_userdic/dic/ipadic_combined_ng_words.dic', # NG words統合版
                        #   '/app/src/mecab/mecab_userdic/dic/ipa_medical_202410.dic', # 病気
                        #   '/app/src/mecab/mecab_userdic/dic/ipa_criminal_202410.dic', # 犯罪
                        #   '/app/src/mecab/mecab_userdic/dic/ipa_religion_202412.dic', # 宗教
                        #   '/app/src/mecab/mecab_userdic/dic/ipa_religion_believer_noun_202412.dic', # 宗教 信者-名詞
                        #   '/app/src/mecab/mecab_userdic/dic/ipa_religion_tuushou_202412.dic', # 宗教 通称
                        #   '/app/src/mecab/mecab_userdic/dic/ipa_race_ethnic_generation_202412.dic', # 人種，民族，世系
                          ]

        self.tagger = MeCab.Tagger('-u ' + ','.join(user_dic_paths)) # 複数指定 -> -u <path2dic1>,<path2dic2>,...
        self.tagger.parse('')

    def parse(self, txt):
        return self.tagger.parse(txt)

    def get_parsedNode(self, txt):
        return self.tagger.parseToNode(txt)

    def get_wakati_by_parseNode(self, txt):
        node = self.get_parsedNode(txt)
        wakati = []
        while node:
            if node.surface == "":
                node = node.next
                continue
            else:
                wakati.append(node.surface)
            node = node.next
        return wakati
    
    def print_parse_by_node(self, txt):
        node = self.get_parsedNode(txt)
        while node:
            if node.surface == "":
                node = node.next
                continue
            else:
                # なにかの処理
                print(f"{node.surface},{node.feature}")
                #print(node.surface)
            node = node.next
        return None

    def _match_properNoun_place(self, features):
        return True if features[1] == '固有名詞' and features[2] == '地域' else False

    def _match_properNoun_lastName(self, features):
        return True if features[2] == '人名' and features[3] == '姓' else False

    def _match_properNoun_firstName(self, features):
        return True if features[2] == '人名' and features[3] == '名' else False

    def _match_properNoun_jinmei(self, features):
        """ neologd はfullnameを1形態素として扱う """
        return True if features[1] == '固有名詞' and features[2] == '人名' and features[3] == '一般' else False


    # ======= フルネーム判定 ======
    def detect_fullname(self, parsedNode, return_mecab_node=False, debug=False):
    # def detect_fullname(self, txt, debug=False):
        """形態素で姓,名と続くものを抽出
        """
        fullnames = []
        _tmp_full_name = []

        # node = self.get_parsedNode(txt)
        node = parsedNode
        while node:
            if node.surface == "":
                node = node.next
                continue
            else:
                # main処理
                if debug:
                    print(f"{node.surface},{node.feature}")
                features = node.feature.split(',')  # 品詞,品詞細分類1,品詞細分類2,品詞細分類3,活用形,活用型,原形,読み,発音

                # 姓の検出 (名詞,固有名詞,地域) or (名詞,固有名詞,人名,姓)
                if self._match_properNoun_lastName(features) or self._match_properNoun_place(features):
                    if debug:
                        print(f'detect 姓: {node.surface}')
                    _tmp_full_name.append(node)
                    node = node.next  # goto next morpheme
                    continue

                # 姓が見つかった上で，名の検出: (名詞,固有名詞,人名,名)
                if len(_tmp_full_name) >= 1:
                    if self._match_properNoun_firstName(features):
                        if debug:
                            print(f'detect 名: {node.surface}')
                        # fullnamesに追加
                        fullnames.append([_tmp_full_name[0], node])
                        _tmp_full_name = []
                    else:
                        # not fullname, then clear
                        _tmp_full_name = []

            node = node.next  # goto next morpheme
        if return_mecab_node:
            return fullnames
        else:
            # fullnameの文字列のみを返す
            return [last_first[0].surface + last_first[1].surface for last_first in fullnames]

    
    # ======= NgWords判定 ======
    def detect_NgWords_by_userdic(self, parsedNode, mecabUserDicTag2NgTag:dict, debug=False) -> tuple:
        """形態素でNgWordsを抽出. 検出したら即時return
        Returns:
            bool: NgWordsが含まれるかどうか
            str: NgWordsのユーザ辞書識別用タグ
        """
        user_dic_tag_idx = 9    # IPA dictionaryの場合
        ngwords = []
        node = parsedNode
        while node:
            if node.surface == "":
                node = node.next
                continue
            else:
                # main処理
                features = node.feature.split(',')
                if debug:
                    print(f"{node.surface},{node.feature}")
                    print([(i, feat) for i, feat in enumerate(features)])
                

                if len(features) >= user_dic_tag_idx+1: # mecab user_dic のtagが存在するか
                    if features[user_dic_tag_idx] in mecabUserDicTag2NgTag.keys():
                        return True, mecabUserDicTag2NgTag.get(features[user_dic_tag_idx])

            node = node.next

        return False, None

    def detect_all_words_by_userdic(self, parsedNode, mecabUserDicTag2NgTag:dict, debug=False) -> list:
        """指定するユーザ辞書識別用タグにマッチした単語リストを取得
        Returns:
            list: ユーザ辞書識別用タグにマッチした単語リスト
        """
        user_dic_tag_idx = 9    # IPA dictionaryの場合
        matched_words = []
        node = parsedNode
        while node:
            if node.surface == "":
                node = node.next
                continue
            else:
                # main処理
                features = node.feature.split(',')
                if debug:
                    print(f"{node.surface},{node.feature}")
                    print([(i, feat) for i, feat in enumerate(features)])
                
                if len(features) >= user_dic_tag_idx+1: # mecab user_dic のtagが存在するか
                    if features[user_dic_tag_idx] in mecabUserDicTag2NgTag.keys():  # いずれかのuserdicにマッチすれば追加
                        matched_words.append(node.surface)
            node = node.next

        return matched_words

    def detect_NgWords_by_wordDB(self, parseNode, ng_word_db:dict) -> tuple:
        """NG wordのdict-DBを利用した判定
        Returns:
            bool: NgWordsが含まれるかどうか
            str: NgWordsの単語
            str: NgWordsDB-file名
        """
        
        # 記事中に存在するすべての表層形集合とNG wrods集合のANDを取る
        doc_hyousou = []
        node = parseNode
        while node:
            if node.surface == "":
                node = node.next
                continue
            else:
                doc_hyousou.append(node.surface)
            node = node.next
        ng_words = list(set(doc_hyousou) & set(ng_word_db.keys()))
        
        if len(ng_words) > 0:
            return True, ng_words[0], ng_word_db[ng_words[0]]
        else:
            return False, None, None


### test
# fullname test
def parseTest():
    txt = "私は山田太郎です。赤星憲広です。ADHDという病気が存在します。"
    mecab = MeCabClass()
    mecab.print_parse_by_node(txt)
    fullnames = mecab.detect_fullname(txt, debug=True)
    for last_first in fullnames:
        print(f'姓: {last_first[0].surface}-名: {last_first[1].surface}')


# NgWords test
def parseNGWords():
    # txt = "ADHDという病気が存在します．また，アレルギー性肉芽腫性血管炎という病気も存在します"
    txt="がん闘病中の山田花子が髪型を黒髪ショートに!すごく似合っていてかっこいいが女ではないwww\n元プロレスラーでがん闘病中の山田が...nこっちのほうがカッコよくて似合ってる!!"
    mecabUserDicTag2NgTag = {'medical_202410': 'med'}


    mecab = MeCabClass()
    parsedNode = mecab.get_parsedNode(txt)
    print(mecab.detect_NgWords_by_userdic(parsedNode, mecabUserDicTag2NgTag, debug=True))


if __name__ == "__main__":
    # parseTest()
    parseNGWords()