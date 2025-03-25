# -*- coding: utf-8 -*-

# hojichar pipelineに PPI判定分類器を組み込み，フィルタリングを行う
# src/privacy_classifier にあるPPI判定器を利用し，hojichar document filterとして処理するようラップしたクラス


import sys
import os
from pathlib import Path
import json

import hojichar
from hojichar import document_filters, Document
import joblib


### SRC
SRC_PATH = str(Path(__file__).resolve().parents[1])
sys.path.append(SRC_PATH)

from privacy_classifier.modules.doc2matrix import PrivacyParser


class PrivacyClassifier(hojichar.core.filter_interface.Filter):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parser = PrivacyParser()
        self.clf_path = SRC_PATH + "/privacy_classifier/MultinomialNB_5_1_0.5_{'alpha': 1e-09}.pkl" # TODO specify trained classifier model path
        self.clf = joblib.load(self.clf_path)
    
    def apply(self, doc: Document) -> Document:
        """
        NB分類器を用いて，文章が要配慮個人情報であるかを判定
        """
        text = doc.text
        X = self.parser.convert_text2matrix([text])
        y_pred = self.clf.predict(X)
        # print(f"y_pred: {y_pred}")

        if int(y_pred[0]) == 1:
            # 要配慮個人情報に該当
            doc.is_reject = True
        

        return doc