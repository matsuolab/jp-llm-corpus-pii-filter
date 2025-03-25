# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path
import pprint
import time
import pickle

import pandas as pd
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.naive_bayes import MultinomialNB



### PROJ
PROJ_PATH = str(Path(__file__).resolve().parents[2])
# print(SRC_PATH)
sys.path.append(PROJ_PATH)
from src.PPI_classifier.extract_keyword_features_controller import KeywordFeaturesExtractor, FullnameFeaturesExtractor, SentenceContainTargetAndWord
from src.PPI_classifier.extract_features_controller import NgramCountVectorizer


class PPI_NaiveBaysianClassifier(object):
    def __init__(self) -> None:
        self.pipeline = None
  
    def set_pipeline(self, pipeline):
        self.pipeline = pipeline



# ----------------------------------------------------------------------------------------------------------------------
# NB classifier の作成と保存, 推論テストコード

def get_NB_classifier_pipeline():
    ppi_ng_dic_files = ['/app/data/db/medical_history_ja_202410.txt',
                        '/app/data/db/criminal_history_ja_202410.txt',
                        '/app/data/db/religion_ja_202412.txt',
                        '/app/data/db/religion_believer_noun_ja_202412.txt',
                        '/app/data/db/religion_tuushou_unique_ja_202412.txt',
                        '/app/data/db/race_ethnic_generation_ja_202412.txt',
                        ]
    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('keywords', KeywordFeaturesExtractor(ppi_ng_dic_files, exist_flag=False)),  # keyword not use MeCab
            ('fullname_count', FullnameFeaturesExtractor()),    # fullname not use MeCab
            ('secret_degree', SentenceContainTargetAndWord(ppi_ng_dic_files)), # sentence num containe target and NG word
            ('ngram_count', NgramCountVectorizer(ngram_range=(1, 3))),  # ngram use MeCab
        ])),
        # ----- sparse matrix algorithm -----
        ('classifier', MultinomialNB())
    ])
    return pipeline

def print_results(y_test, y_pred):
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    acc_score = accuracy_score(y_test, y_pred)
    print("Accuracy:", acc_score)
    print("Classification Report:\n", classification_report(y_test, y_pred))
    eval_dict = classification_report(y_test, y_pred, output_dict=True)
    print(confusion_matrix(y_test, y_pred, labels=[1, 0]))  # 上から Positive, Negative
    return eval_dict

def train_NB_classifier(pipeline_save=True):
    """ 2025/03 分類器の訓練と評価，訓練済みpipelineの保存
    dataset: cc + synthetic(geminiのみ)
    """
    PPIClassifier = PPI_NaiveBaysianClassifier()
    
    # Dataset - Train
    from src.PPI_classifier.data_controller import PPIDatasetController
    from sklearn.model_selection import train_test_split
    DataCtr = PPIDatasetController()
    cc = DataCtr.cc()       # neg>
    cc_202412 = DataCtr.ano_202412_cc()     # neg>
    pseudo_ppi_cc_202501 = DataCtr.ano_pseudo_ppi_cc202501(deal_positive_all=False,only_use_positive=False) # gemini生成
    gemini5000 = DataCtr.gemini_better()
    train_df = pd.concat([cc, cc_202412, gemini5000,pseudo_ppi_cc_202501], axis=0, ignore_index=True)
    train_df = DataCtr.down_sampling(train_df, non_privacy_rate=1, seed=42) # down sampling
    print(f"train_df: {train_df.shape}")
    print(train_df['is_privacy'].value_counts())
    from sklearn.model_selection import train_test_split
    X_train, X_valid, y_train, y_valid = train_test_split(train_df['text'], train_df['is_privacy'], test_size=0.1, random_state=42)

    # Test Dataset
    test_df = DataCtr.ano_test20241007()

    # Pipeline
    pipeline = get_NB_classifier_pipeline()
    PPIClassifier.set_pipeline(pipeline)
    PPIClassifier.pipeline.fit(X_train, y_train)    # Train

    # Evaluation
    # valid
    s_time = time.time()
    y_pred = PPIClassifier.pipeline.predict(X_valid)
    print_results(y_valid, y_pred)
    elapsed_time = time.time() - s_time
    print(f'valid-predict elapsed_time: {elapsed_time}, proc/1instance: {elapsed_time/len(y_valid):.5f}')

    # test
    s_time = time.time()
    test_y_pred = PPIClassifier.pipeline.predict(test_df['text'])
    print_results(test_df['is_privacy'], test_y_pred)
    elapsed_time = time.time() - s_time
    print(f'test-predict elapsed_time: {elapsed_time}, proc/1instance: {elapsed_time/len(test_y_pred):.5f}')

    # Save
    if pipeline_save:
        save_pipeline_path = PROJ_PATH+'/src/PPI_classifier/models/tmp/NB_pipeline_202503_2.pkl'
        with open(save_pipeline_path, 'wb') as f:
            pickle.dump(PPIClassifier.pipeline, f)
        print(f'saved model -> {save_pipeline_path}')


def test_load_inference():
    """ 訓練済みscikit-learn pipelineを読み込んで推論するテスト """
    trained_pipeline = None
    save_model_path = PROJ_PATH+'/src/PPI_classifier/models/tmp/ppi_classfier.pkl'
    with open(save_model_path, 'rb') as f:
        trained_pipeline = pickle.load(f)
        print(f'loaded trained_pipeline: type={type(trained_pipeline)}')

    PPICls = PPI_NaiveBaysianClassifier()
    PPICls.set_pipeline(trained_pipeline)

    from src.PPI_classifier.data_controller import PPIDatasetController
    DataCtr = PPIDatasetController()
    test_df = DataCtr.ano_test20241007()

    s_time = time.time()
    y_ret = []
    for idx, row in test_df.iterrows():
        text = row['text']
        print(f"{idx=}, {text}")
        
        y_pred = PPICls.pipeline.predict([text])
        print(f"{y_pred[0]=}")
        y_ret.append(y_pred[0])
    elapsed_time = time.time() - s_time
    print(f"elapsed_time: {elapsed_time}, {elapsed_time/len(test_df)} sec/inst")
    test_df['is_privacy_by_classifier'] = y_ret
    test_df.to_json(PROJ_PATH+'/src/PPI_classifier/tmp_output/tmp/test_out.jsonl', orient='records', force_ascii=False, lines=True)

if __name__ == "__main__":
    train_NB_classifier(pipeline_save=True)
    # test_load_inference()