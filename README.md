# 要配慮個人情報フィルター
本コードは，大規模言語モデル（LLM）の学習用コーパスから，個人情報の中でも特に配慮が求められる「要配慮個人情報」をフィルタリングするためのものです.  

大規模なデータセットに含まれる要配慮個人情報のすべてを目視で確認することは困難であるため，本フィルターは一定の配慮として適用することを想定しています. そのため，本コードにより完全にすべての要配慮個人情報を排除できるものではない点について，あらかじめご了承ください.  

具体的には，CommonCrawlのようなテキストをtext属性として含むjsonl形式のデータに対し，要配慮個人情報を含むか否かを判定しフィルターします. フィルタリング処理にはhojicharライブラリを用いています.   

現在のフィルターは，以下の2つの条件を基に判定を行っています.  

ルールベース判定：全文中に氏名とNGワードがともに存在するか否か.  

分類器による判定：機械学習による要配慮個人情報（PPI）分類器を用いた判定.  

## 実行方法
### (準備) フィルターに用いる学習済み要配慮個人情報判定器のDL
- 学習済みの判定器pickleファイル(450.7Mb)を以下のlinkから取得し, `配置先`にpickleファイルを置く.
    - pickleファイル取得URL : https://drive.google.com/file/d/11n-FN_YypJjnzsiL_pHUhYxGIsswSByw/view?usp=drive_link
    - 配置先: <project>/src/PPI_classifier/models/NB_pipeline_202503.pkl
    - NOTE: <project>/src/filtering/custom_document_filter_PPI_rule_and_classifier.py の中で読み込まれる.

### Dockerを用いた実行環境作成
以下に示す2つのプログラム実行方法に応じたコンテナ作成を行ってください
- 方法A-コンテナ内でプログラム実行版: コンテナの中でインタラクティブにコマンドを実行する方法
- 方法B-コンテナ外からプログラム実行版: コンテナを一時的に立ち上げ，フィルタ処理を実行する方法

- 作成するコンテナ情報
    - ubuntu, python, mecab(ipadicをデフォルト辞書として利用)を備えたコンテナを作成する

#### 方法A-コンテナ内でプログラム実行版
- 1. docker image の作成
    ```sh
    - image作成時にmecab, mecab辞書設定ファイルを使用するため，<project>/docker/install_mecab_ipadicフォルダを <project>/docker/dockerfiles にコピー配置する．

    $ cd <project>/docker/dockerfiles
    $ docker build -t ppi_filter . --no-cache     # image名 ppi_filterとする場合
    $ docker images     # image確認
    # -> imageが作成される
    ```

- 2. docker container起動
    ```sh
    # container起動 projectコードは/appにマウントする．(MeCabユーザ辞書などの読み込みが/app以下を想定している記述のため)
    $ docker run --name ppi_filter_app -v <project_path>:/app -it ppi_filter

    # containerに入る
    $ docker exec -it ppi_filter_app /bin/bash
    ```

- 3. フィルタリングの実行
    - jsonl形式のファイルを持つ入力ディレクトリを引数でプログラムに与え，プログラムは入力ディレクトリに存在するすべてのファイルについてフィルタリング処理を行う．処理後に指定された出力ディレクトリにファイルごとのフィルタリング結果を保存する．

    - 入力ディレクトリにある入力ファイル形式の要件
        - ファイル名は任意
        - 各行が1つの JSON オブジェクト になっている（改行区切り）(jsonl形式)
        - key と値のペアで構成される．フィルタ対象のkeyを必ず含むこと

    - 出力ディレクトリで出力されるファイル形式の要件
        - 入力されたファイルにつき以下のファイルを出力
            | ファイル名 | 説明 |
            | ---- | ---- |
            | passed_<入力ファイル名> | フィルタをパスしたデータ．<br>現状: 1jsonオブジェクトは入力時のkey-value情報を保持 (**注意: フィルタで入力されたファイルの先頭jsonオブジェクトに定義されているkeyを保持対象にする．したがって，ファイルの先頭に定義されていないkeyについては無視される．**)|
            | stat_<入力ファイル名> | フィルタの統計や処理についての情報 |
            | rejected_<入力ファイル名> | フィルタで除外されたデータ. --skip_rejected optionを与えなかった場合に本ファイルが作られる |
        - 入力各行が1つの JSON オブジェクト

    - プログラムの実行
        ```sh
        # コンテナ内
        $ cd /app/src/filtering/

        ### 基本的な使用例
        # --input_dir は 必須引数 で、処理するドキュメントを含むディレクトリを指定
        # --output_dir は省略可能で、デフォルト値 "./tmp_output/tmp" が使用
        $ python3 respect_PI_filter.py --input_dir <input_jsonl_dir_path>

        (e.g.)
        # 処理対象ディレクトリの作成とファイルの準備. ここでは<project>/data/test_filter ディレクトリを作成し，その中にフィルタリングしたいjsonlファイルを配置 (コンテナ内の場所: /app/data/test_filter/) 
        
        $ python3 respect_PI_filter.py --input_dir /app/data/test_filter/
        # <project>/src/filtering/tmp_output/tmp/ 以下に結果ファイルができる

        ### 出力ディレクトリの指定
        $ python3 respect_PI_filter.py --input_dir ./data --output_dir ./output

        ### 並列処理を有効にする
        $ python3 respect_PI_filter.py --input_dir ./data --n_workers 2

        ### フラグオプションの利用
        $ python3 respect_PI_filter.py --input_dir ./data --skip_rejected --dump_reason

        ```

        - メインプログラム引数 (<project>/src/filtering/respect_PI_filter.py)
            | Option | 説明 | default |
            | ---- | ---- | --- |
            | --input_dir | 入力データのディレクトリ | --- |
            | --output_dir | 出力データのディレクトリ | "./tmp_output/tmp" |
            | --n_workers | 並列処理ワーカ数 | 1 |
            | --filter_key | フィルタリング対象のkey | "text" |
            | --skip_rejected | (flag) フィルタ処理でrejectedデータを出力しない | False |
            | --dump_reason | (flag) hojicjarの出力情報(`filter_is_reject`, `filter_reason`)を記事ごとのjsonオブジェクトに付与 | False |

#### 方法B-コンテナ外からプログラム実行版
- 1. docker image の作成
    ```sh
    # 本projectディレクトリ直下で以下のコマンドでimageを作成 (フィルタに必要なファイルをコピーしコンテナimageにて/app以下に配置するため)
    # ここでは作成image名を ppi_filter_mount_run とする. 
    
    $ cd <project>
    <project> $ docker build -f ./docker/mount_run/Dockerfile -t ppi_filter_mount_run . --no-cache
    ```
    - dockerfileにてENTRYPOINTを利用し，直接プログラム実行可能な状態のimageができる．

- 2. プログラムの実行
    - 処理したいディレクトリを指定し，コンテナ上にマウントする. マウントしたディレクトリをメインプログラムの引数に指定し処理を行う．処理後コンテナは削除される．
    - 指定できる引数は 方法A-コンテナ内でプログラム実行版 のメインプログラム引数を参照すること．
        - **注意: option　`--output_dir` を必ず使用し，マウントしたディレクトリ以下を指定すること．** そうでない場合には，プログラム処理後コンテナが削除されるためフィルタ結果ファイルも得られない．
    ```sh
    # 処理対象ディレクトリの作成とファイルの準備. ここでは<project>/data/test_filter ディレクトリを作成し，その中にフィルタリングしたいjsonlファイルを配置

    # 以下のコマンドは，<project>/data をコンテナ上の/mntにマウントし，マウントポイント内のtest_filterディレクトリをフィルタプログラムの入力として与える．出力pathは，マウントポイントの/mnt/filter_out ディレクトリに出力する

    <project> $ docker run --rm -v ./data:/mnt ppi_filter_mount_run --input_dir /mnt/test_filter --output_dir /mnt/filter_out

    # -> <project>/data/filter_out (コンテナ内から見たpath: /mnt/filter_out) にフィルタ結果ファイル (passed_, rejected_, stat_) が出力される．
    ```


# 補足
## Rulebase フィルタのための新規NGワード登録，MeCabユーザ辞書作成方法, ファイルタへの適用方法
- MeCabユーザ辞書(~.dic)を作成する．または新たに単語などを登録したい場合に行うこと
- 現状, MeCabユーザ辞書の指定をfull pathを与えている. ここではdockerを用いて, /app/に本プロジェクトをmountしている前提になっている.
- 1. 1行1単語の形式でNGワードリストファイル(~.txt)から，MeCabユーザ辞書登録用csv(ipadic向け)を作成し，ユーザ辞書としてコンパイルする．
    - src/mecab/create_user_dic.py - create_ipa_conbined_keyword()
        - 複数のキーワードファイルのpath とユーザ辞書に付与したい識別用タグを指定する
        - ユーザ辞書を識別するためにtagger.parseToNodeで得られるNode.featureの末尾(featureの10番目)に識別用タグ(`dic_tag`)を追加する
        - 実行すると, ユーザ辞書作成のための.csvと ユーザ辞書(.dic) が得られる
        - ユーザ辞書を <project>/src/mecab/mecab_userdic/dic/ 以下に配置

- 2. 追加したユーザ辞書を，フィルタリング処理プログラムに反映させる
    - MeCab処理クラスに，ユーザ辞書のパスを追記
        - src/mecab/MeCabClass.py
        ```py
        user_dic_paths = ['/app/src/mecab/mecab_userdic/dic/ipa_jinmei_v3.dic',     # 人名
                          '/app/src/mecab/mecab_userdic/dic/ipadic_combined_ng_words.dic', # NG words統合版　<- ユーザ辞書のpath追加
                            ...
                            ]
        ```

    - filter関数に追加
        - src/filtering/custom_document_filter_PPI_rule_and_classifier.py
            - 以下の2箇所をユーザ辞書に用いたワードリストファイルのパスと，ユーザ辞書の識別用タグを記載する
        ```py
        def __init__(self, *args, **kwargs) -> None:
            ...

            ### NG words user辞書判定されなかったときに，形態素として一致していればNGとする
            ng_key_dic_file_paths = ['/app/data/db/medical_history_ja_202410.txt',
                                    '/app/data/db/criminal_history_ja_202410.txt', # <- [追記1] NGワードリストファイルのパスを追記
                                    ...
                                    ]



            ### MeCab NG words
            self.mecabUserDicTag2NgTag = {'medical_202410': 'userd-med',
                                        'criminal_202410': 'userd-criminal'}    # <- [追記2] 識別用タグ: デバッグ時の出力用タグ


        ```

## フォルダ構造
```
./docker                        docker環境構築
./docker/dockerfiles            mecab, ライブラリ導入されたdocker作成. 方法A-コンテナ内でプログラム実行版
./docker/install_mecab_ipadic　 mecab導入時に使用するもの．mecab辞書読み込み設定ファイル
./docker/mount_run              方法B-コンテナ外からプログラム実行版

./data
./data/db                       NGキーワードを持つ.txtファイル

./src
./src/PPI_classifier            分類器を用いたPPI判定器
./src/filtering                 filteringを行うコード
./src/mecab                     Rulebase filterのためのmecabクラス
./src/mecab/mecab_userdic       (NG)キーワードを持つ.txtからmecabユーザ辞書としてコンパイルしたものを配置
```
