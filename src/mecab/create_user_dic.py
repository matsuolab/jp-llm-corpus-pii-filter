# -*- coding: utf-8 -*-
# MeCabのユーザ辞書csvを作成する

import os
import jaconv   # pip install jaconv ひらがな -> カタカナ変換


def create_ipa_conbined_keyword():
    """指定されたNGキーワードを含むファイルからNGword用のmecab-user辞書を作成．
    Returns:
        ユーザ辞書作成用 ~.csv
        mecabユーザ辞書 ~.dic
    """
    out_csv_and_dic_name = 'ipadic_combined_ng_words'
    cost = 10000
    NGkeyword_filePath_DicTag = {
        '/app/data/db/medical_history_ja_202410.txt': 'medical_202410',
        '/app/data/db/criminal_history_ja_202410.txt': 'criminal_202410',
        '/app/data/db/religion_ja_202412.txt': 'religion_202412',
        '/app/data/db/religion_believer_noun_ja_202412.txt': 'religion_believer_noun_202412',
        '/app/data/db/religion_tuushou_unique_ja_202412.txt': 'religion_tuushou_202412',
        '/app/data/db/race_ethnic_generation_ja_202412.txt': 'race_ethnic_generation_202412',
    }

    # 重複を除くNG wordsを全て取得
    all_ng_words_dictag = {}    # {word: dic_tag}
    for f_path, dic_tag in NGkeyword_filePath_DicTag.items():
        in_f = open(f_path, 'r', encoding='utf-8')
        for line in in_f:
            w = line.strip()
            if w not in all_ng_words_dictag.keys():
                all_ng_words_dictag[w] = dic_tag
            else:
                print(f"重複のためskip: {w} {f_path=} {dic_tag=}")
                
    # user dic作成用のcsvを出力
    out_csv_path = f"./{out_csv_and_dic_name}.csv"
    out_f = open(out_csv_path, 'w', encoding='utf-8')
    for w, dic_tag in all_ng_words_dictag.items():
        # 品詞体系に従う必要あり https://www.unixuser.org/~euske/doc/postag/#chasen
        # 表層形,左文脈ID,右文脈ID,コスト,品詞,品詞細分類1,品詞細分類2,品詞細分類3,活用型,活用形,原形,読み,発音,追加情報(辞書タグ)
        dic_format = f'{w},,,{cost},名詞,一般,*,*,*,*,*,*,*,{dic_tag}'
        out_f.write(f"{dic_format}\n")

    print(f'out ->{out_csv_path} total words: {len(all_ng_words_dictag.keys())}')

    # csvからuser dicをコンパイル
    # ユーザー辞書をコンパイル
    out_userdic_path = f"{out_csv_and_dic_name}.dic"
    os.system(f"/usr/lib/mecab/mecab-dict-index -f utf-8 -t utf-8 -d /usr/lib/aarch64-linux-gnu/mecab/dic/ipadic -u {out_userdic_path} {out_csv_path}")
    print(f'out -> mecab-userdic: {out_userdic_path}')

def _output_ipa_csv(input_path, output_csv_path, cost, dic_tag):
    in_f = open(input_path, 'r', encoding='utf-8')
    out_f = open(output_csv_path, 'w', encoding='utf-8')
    line_num = 0
    for line in in_f:
        line_num += 1
        w = line.strip()
        # 品詞体系に従う必要あり https://www.unixuser.org/~euske/doc/postag/#chasen
        # 表層形,左文脈ID,右文脈ID,コスト,品詞,品詞細分類1,品詞細分類2,品詞細分類3,活用型,活用形,原形,読み,発音,追加情報(辞書タグ)
        dic_format = f'{w},,,{cost},名詞,一般,*,*,*,*,*,*,*,{dic_tag}'
        out_f.write(f"{dic_format}\n")

    print(f'out->{output_csv_path} {line_num=}')

def create_ipa_only_keyword():
    ### 病気 (英文字込 spaceなし)
    # keyword_list_path = '/app/data/db/medical_history_ja_202410.txt'
    # out_csv_path = './ipadic_medical_202410.csv'
    # dic_tag = 'medical_202410'

    ### 犯罪
    # keyword_list_path = '/app/data/db/criminal_history_ja_202410.txt'
    # out_csv_path = './ipadic_criminal_202410.csv'
    # dic_tag = 'criminal_202410'

    ### 宗教
    # 宗教名list
    # keyword_list_path = '/app/data/db/religion_ja_202412.txt'
    # out_csv_path = './ipadic_religion_202412.csv'
    # dic_tag = 'religion_202412'
    
    # 宗教名通称
    # keyword_list_path = '/app/data/db/religion_tuushou_unique_ja_202412.txt'
    # out_csv_path = './ipadic_religion_tuushou_202412.csv'
    # dic_tag = 'religion_tuushou_202412'
   
    # 信者, 信徒-名詞
    # keyword_list_path = '/app/data/db/religion_believer_noun_ja_202412.txt' 
    # out_csv_path = './ipadic_religion_believer_noun_202412.csv'
    # dic_tag = 'religion_believer_noun_202412'

    ### 人種，民族，世系など
    keyword_list_path = '/app/data/db/race_ethnic_generation_ja_202412.txt'
    out_csv_path = './ipadic_race_ethnic_generation_202412.csv'
    dic_tag = 'race_ethnic_generation_202412'

    cost = 10000
    
    _output_ipa_csv(keyword_list_path, out_csv_path, cost, dic_tag)


def create_ipa_jinmei_v3():
    keyword_list_path = '/app/data/db/name_dic/unpack_jinmei30/JINMEI30_cutTop.TXT'
    out_csv_path = './ipadic_jinmei_v3.csv' 
    cost = 10000
    dic_tag = 'jinmei_v3'

    in_f = open(keyword_list_path, 'r', encoding='utf-8')
    out_f = open(out_csv_path, 'w', encoding='utf-8')
    line_num = 0
    for line in in_f:
        line_num += 1
        hira, kanji_seimei = line.strip().split('\t')
        kanji, sei_or_mei = kanji_seimei.replace('\"', "").split(":")
        kata = jaconv.hira2kata(hira)
        dic_format = f'{kanji},,,{cost},名詞,固有名詞,人名,{sei_or_mei},*,*,{hira},{kata},{kata},{dic_tag}'
        # print(dic_format)
        out_f.write(f"{dic_format}\n")

    print(f'out->{out_csv_path} {line_num=}')


if __name__ == "__main__":
    create_ipa_conbined_keyword()   # 各wordリストを結合して単一のuser dicを作成
    # create_ipa_only_keyword()   # wordリストごとにuser dicを別に作成
    # create_ipa_jinmei_v3()    # word+読みあり
    