# -*- coding: utf-8 -*-

# (1) Process files one by one.
# python respect_PI_filter.py --input_dir /app/data/test_filter/labeled/ --output_dir /app/src/filtering/tmp_output/tmp/ --n_workers 1 --filter_key text --skip_rejected

# (2) Process files with multi-processing.
# python respect_PI_filter.py --input_dir /app/data/test_filter/labeled/ --output_dir /app/src/filtering/tmp_output/tmp/ --n_workers 2 --filter_key text --skip_rejected

# (3) output rejected data (remove flag `--skip_reject`) and see filter reason
# python respect_PI_filter.py --input_dir /app/data/test_filter/labeled/ --output_dir /app/src/filtering/tmp_output/tmp/ --n_workers 1 --filter_key text --dump_reason

from datetime import datetime
import json
from hojichar import document_filters, tokenization, Compose, Document
import argparse
import sys
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

### SRC
SRC_PATH = str(Path(__file__).resolve().parents[1])
# print(SRC_PATH)
sys.path.append(SRC_PATH)

# from filtering.custom_document_filter_PPI import ProtectPersonalInformationJa_v1    # mecab rule-based filter
# from filtering.custom_document_filter_PPI_classifier import PrivacyClassifier    # NB classifier filter
from filtering.custom_document_filter_PPI_rule_and_classifier import ProtectPersonalInformationRulebaseAndClassifier    # mecab rule-based filter + NB classifier filter
from filtering.custom_document_filter_detail_jsondumper import DetailDocument, CustomMetaInfoJSONLoader, CustomMetaInfoJSONDumper, JSONDumperWithKeepExtras


def __readlines(input_file: str):
    with open(input_file) as fp:
        return fp.readlines()

def get_files(inpud_dir: str):
    return [f for f in os.listdir(inpud_dir) if os.path.isfile(os.path.join(inpud_dir, f))]

def process_protect_PI_ja(inputs: tuple):
    """
    Returns:

    """
    print(f"{inputs=}")
    jsonl_filename, input_dir, output_dir, filter_key, skip_rejected, dump_reason = inputs
    lines = __readlines(os.path.join(input_dir, jsonl_filename))
    print(f"processing ... {str(os.path.join(input_dir, jsonl_filename))}")

    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)

    # Filter pipeline
    cleaner = Compose([
        # Input
        document_filters.JSONLoader(key=filter_key),      # original
        # CustomMetaInfoJSONLoader(key=filter_key),             # custom loader for see meta info details
        
        # Document Filter 
        # 各filterについて，(default)skip_rejected=Trueである -> doc.is_reject = True になった場合，後続のフィルタは無意味なので後続の処理はskipされる
        # ProtectPersonalInformationJa_v1(),  # mecab rule-based filter
        # PrivacyClassifier(),  # NB classifier filter

        ProtectPersonalInformationRulebaseAndClassifier(add_ppi_info=False),  # mecab rule-based filter + NB classifier filter

        # Output
        document_filters.JSONDumper(skip_rejected=skip_rejected, dump_reason=dump_reason),    # original
        # CustomMetaInfoJSONDumper(dump_reason=True),    # custom dumper for see meta info details
    ])

    # Apply filter & write to file
    passed_writer = open(os.path.join(output_dir, f"passed_{jsonl_filename}"), "w")  # 
    if skip_rejected is False:
        rejected_writer = open(os.path.join(output_dir, f"rejected_{jsonl_filename}"), "w")
    
    for line in lines:
        result = cleaner.apply(Document(line))
        # result = cleaner.apply(DetailDocument(line))    # NOTE: 処理中のmeta情報を保持する場合のDocument class
        if result.is_rejected is True:
            if skip_rejected is False:
                rejected_writer.write(result.text + "\n")
        else:
            passed_writer.write(result.text + "\n")

    passed_writer.close()
    if skip_rejected is False:
        rejected_writer.close()

    # write statistics info    
    with open(os.path.join(output_dir, f"stat_{jsonl_filename}"), "w") as writer:
        writer.write(json.dumps(cleaner.statistics, ensure_ascii=False) + "\n")

def process_protect_PI_ja_test(inputs: tuple):
    """1 jsonlに対してfilter
    meta情報を保持し，処理のdebug用途に使用
    """
    jsonl_filename, input_dir, output_dir, filter_key, skip_rejected, dump_reason = inputs
    lines = __readlines(os.path.join(input_dir, jsonl_filename))
    print(f"processing ... {str(os.path.join(input_dir, jsonl_filename))}")
    
    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)

    # Filter pipeline
    cleaner = Compose([
        # Input
        CustomMetaInfoJSONLoader(key=filter_key, metadata_keys=['is_sensitive_personal_information', 'reason']),    # add metadata
        # Document Filter
        # document_filters.DocumentNormalizer(),  # NFKC正規化
        # ProtectPersonalInformationJa_v1(),
        # PrivacyClassifier(),  # NB classifier filter
        ProtectPersonalInformationRulebaseAndClassifier(add_ppi_info=True),  # mecab rule-based filter + NB classifier filter

        # Output
        CustomMetaInfoJSONDumper(dump_reason=dump_reason),    # custom dumper for see meta info details NOTE: rejectも書き出したいので，skip_rejectedを渡さない(skip_rejected=False)
    ])

    # Apply filter & write to file
    # 1つのjsonlファイルに結果をすべて書き込む
    with open(os.path.join(output_dir, f"applied_filter_{jsonl_filename}"), "w") as writer:
        for line in lines:
            # result = cleaner.apply(Document(line))
            result = cleaner.apply(DetailDocument(line))    # NOTE: 処理中にもinput jsonlのmeta情報を保持するためのDocument class
            writer.write(result.text + "\n")
                # remained_lines.append(result.text)

    with open(os.path.join(output_dir, f"stat_{jsonl_filename}"), "w") as writer:
        writer.write(json.dumps(cleaner.statistics, ensure_ascii=False) + "\n")

def process_protect_PI_ja_keep_kv(inputs: tuple):
    """
    Returns:

    """
    print(f"{inputs=}")
    jsonl_filename, input_dir, output_dir, filter_key, skip_rejected, dump_reason = inputs
    lines = __readlines(os.path.join(input_dir, jsonl_filename))
    print(f"processing ... {str(os.path.join(input_dir, jsonl_filename))}")

    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)

    # Determine the key-value to keep except `filter_key` from the first json
    head_data = json.loads(lines[0])
    extra_keys = list(set(head_data.keys()) - set([filter_key]))

    # Filter pipeline
    cleaner = Compose([
        # Input
        document_filters.JSONLoader(key=filter_key, extra_keys=extra_keys),      # original
        
        # Document Filter 
        # 各filterについて，(default)skip_rejected=Trueである -> doc.is_reject = True になった場合，後続のフィルタは無意味なので後続の処理はskipされる
        ProtectPersonalInformationRulebaseAndClassifier(add_ppi_info=False),  # mecab rule-based filter + NB classifier filter

        # Output
        # document_filters.JSONDumper(skip_rejected=skip_rejected, dump_reason=dump_reason),    # original: 入力時のfilter_keyの値を`text`の値として出力. extra_keysは出力されない
        JSONDumperWithKeepExtras(main_filter_key=filter_key, skip_rejected=skip_rejected, dump_reason=dump_reason),    # 入力時のkey-val を保持して出力
    ])

    # Apply filter & write to file
    passed_writer = open(os.path.join(output_dir, f"passed_{jsonl_filename}"), "w")  # 
    if skip_rejected is False:
        rejected_writer = open(os.path.join(output_dir, f"rejected_{jsonl_filename}"), "w")
    
    for line in lines:
        result = cleaner.apply(Document(line))
        # result = cleaner.apply(DetailDocument(line))    # NOTE: 処理中のmeta情報を保持する場合のDocument class
        if result.is_rejected is True:
            if skip_rejected is False:
                rejected_writer.write(result.text + "\n")
        else:
            passed_writer.write(result.text + "\n")

    passed_writer.close()
    if skip_rejected is False:
        rejected_writer.close()

    # write statistics info    
    with open(os.path.join(output_dir, f"stat_{jsonl_filename}"), "w") as writer:
        writer.write(json.dumps(cleaner.statistics, ensure_ascii=False) + "\n")

def main_filter(args):
    """ 指定されたinput_dirに含まれるすべてのfileに対してfilterを行う
    Args:
        args.input_dir: input directory containing jsonl files
        args.output_dir: output directory to save files (passed, rejected, stat)
        args.n_workers: number of workers for multi-processing. default=1 (single processing)
        args.filter_key: Define the key in the JSONL file used for filtering records. default="text"
        args.skip_rejected: If is_reject flag is True in hojichar, skip further filter processing and do not include it in output. default=False
        args.dump_reason: hojichar dumps the output information with `is_rejected` and `reason` entries. default=False

    出力ファイル:
        - passed_{filename}: フィルタを通過したデータ
        - rejected_{filename}: フィルタを通過しなかったデータ
        - stat_{filename}: フィルタの統計情報

    設計方針:
    - 1fileに対して，filter処理インスタンスを作成し，処理を実行する方針の実装にした. 
        - (フィルタpipelineを持つクラスから単一のインスタンスを作成し，クラスメソッドで処理するプログラムを記述してみたが，multi process利用時にpipelineで利用される判定機まわりの読み込みでエラーが発生した．)
    """
    print(f"{args=}")
    jsonl_filenames = get_files(args.input_dir)
    print(f"Filtering for total {len(jsonl_filenames)} jsonl files with n_workers={args.n_workers} ...")

    # straitforward implementation
    s_time = time.time()
    with ProcessPoolExecutor(max_workers=args.n_workers) as executor:
        # results = executor.map(process_protect_PI_ja, [(jsonl_fname, args.input_dir, args.output_dir, args.filter_key, args.skip_rejected, args.dump_reason) for jsonl_fname in jsonl_filenames])
        
        # for debug
        # results = executor.map(process_protect_PI_ja_test, [(jsonl_fname, args.input_dir, args.output_dir, args.filter_key, args.skip_rejected, args.dump_reason) for jsonl_fname in jsonl_filenames])

        # keep other kv
        results = executor.map(process_protect_PI_ja_keep_kv, [(jsonl_fname, args.input_dir, args.output_dir, args.filter_key, args.skip_rejected, args.dump_reason) for jsonl_fname in jsonl_filenames])

    for result in results:
        print(result)

    elapsed_time = time.time() - s_time
    print(f"total filter proc time: {elapsed_time=:.3f} sec")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some documents.')
    parser.add_argument('--input_dir', type=str,
                        help='The input directory containing documents to process', required=True)
    parser.add_argument('--output_dir', type=str,
                        help='The input file containing documents to process', required=False, default="./tmp_output/tmp")
    parser.add_argument('--n_workers', type=int,
                        help='number of workers for multi-processing', required=False, default=1)
    parser.add_argument('--filter_key', type=str,
                        help='Define the key in the JSONL file used for filtering records.', required=False, default="text")
    
    # Flag options
    parser.add_argument('--skip_rejected',
                        help='If this flag is used, skip further filter processing in hojichar and do not output rejected data to file', action="store_true")
    parser.add_argument('--dump_reason',
                        help='If this flag is used, hojichar dumps the output information with `filter_is_rejected` and `filter_reason` entries.', action="store_true")
    args = parser.parse_args()

    main_filter(args)