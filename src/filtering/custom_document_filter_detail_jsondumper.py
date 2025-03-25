# -*- coding: utf-8 -*-

from datetime import datetime
import json
from hojichar import document_filters, Document
import argparse
import sys
import os
import time
from pathlib import Path




class JSONDumperWithKeepExtras(document_filters.JSONDumper):
    def __init__(self, main_filter_key:str, dump_reason=False, *args, **kwargs):
        """公式JSONDumperは指定したfilterのためのkey以外のkey-valは削除されるため,
        JSONLoaderで指定したextra_keysのkey-valを保持しjson出力するようにする．
        """
        super().__init__(dump_reason=dump_reason, *args, **kwargs)
        self.main_fileter_key = main_filter_key

    def apply(self, document: Document) -> Document:
        """
        ref: https://hojichar.github.io/HojiChar/hojichar/filters/document_filters.html#JSONDumper
        """
        text = document.text
        return_data = {self.main_fileter_key: text}
        return_data.update(document.extras)
        
        # add hojichar info
        if self.dump_reason:
            return_data.update({
                "filter_is_rejected": document.is_rejected,
                "filter_reason": document.reject_reason,
            })

        document.text = json.dumps(return_data, ensure_ascii=False)
        
        return document



# Debug usage when you want to add custom debug information when executing filtering
# -----------------------------------------------------------------------------------------------------
class DetailDocument(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = {}


# Json load時にmetadataを付与したい場合
class CustomMetaInfoJSONLoader(document_filters.JSONLoader):
    def __init__(self, metadata_keys=[], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata_keys = metadata_keys

    def apply(self, document: Document) -> Document:
        """
        ref: https://hojichar.github.io/HojiChar/hojichar/filters/document_filters.html#JSONLoader
        """
        try:
            data = json.loads(document.text)
            document.text = str(data[self.key])
            # add metadata
            for k in self.metadata_keys:
                document.metadata[k] = data.get(k, None)
        except Exception as e:
            if self.ignore:
                document.is_rejected = True
                return document
            else:
                raise e

        return document
                    
# Json dump時にmetadataを付与したい場合
class CustomMetaInfoJSONDumper(document_filters.JSONDumper):
    def __init__(self, dump_reason=False, *args, **kwargs):
        super().__init__(dump_reason=dump_reason, *args, **kwargs)

    def apply(self, document: Document) -> Document:
        """
        ref: https://hojichar.github.io/HojiChar/hojichar/filters/document_filters.html#JSONDumper
        """
        text = document.text
        if self.dump_reason:
            document.text = json.dumps(
                {
                    "text": text,
                    "is_rejected": document.is_rejected,
                    "reason": document.reject_reason,

                    # TODO : Custom meta info
                    # ---------------------------------------------------------------------
                    # metainfo from input json
                    "sensitive_reason": document.metadata.get('PPI_reason', None),
                    "is_sensitive": document.metadata.get('is_sensitive_personal_information', False),

                    # metainfo from filter
                    "detect_fullnames": document.metadata.get('detect_fullnames', []),
                    "ng_match": document.metadata.get('ng_match', []),
                    # ---------------------------------------------------------------------
                },
                ensure_ascii=False,
            )
        else:
            document.text = json.dumps({"text": text}, ensure_ascii=False)
        
        return document