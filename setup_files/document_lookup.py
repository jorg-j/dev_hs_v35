import unittest
from unittest.mock import ANY
from idplib import ValueUtils
from typing import List, Any, Dict

#### SOF

class DocumentFields:
    def __init__(self, doc: Dict[str, Any]):
        self.document_fields = doc["document_fields"]

    class _Filter:
        def __init__(self, document_fields):
            self.document_fields = document_fields

        def by_field_name(self, field_name: str) -> List:
            return list(
                filter(
                    lambda x: x["field_name"] == field_name
                    and "transcription_normalized" in x,
                    self.document_fields,
                )
            )

        def by_fields_with_value(
            self, field_name: str, value: str, fuzzy: bool = True, threshold: int = 89
        ) -> List:
            fields = self.by_field_name(field_name)

            if fuzzy:
                return [
                    field
                    for field in fields
                    if ValueUtils.Compare.string(
                        field["transcription_normalized"], value, threshold=threshold
                    )
                ]
            else:
                return [
                    field
                    for field in fields
                    if field["transcription_normalized"] == value
                ]

    @property
    def Filter(self):
        return DocumentFields._Filter(self.document_fields)


class DocumentData(DocumentFields):
    def __init__(self, doc: Dict[str, Any]):
        self.doc = doc
        self.layout_name = doc["layout_name"]
        super().__init__(doc)


class Docs:
    def __init__(self, all_documents: List):
        self.all_documents = all_documents

    class _Filter:
        def __init__(self, all_documents):
            self.all_documents = all_documents

        def by_layout(self, layouts: List):
            return [
                doc
                for doc in self.all_documents
                if DocumentData(doc).layout_name in layouts
            ]

    @property
    def Filter(self):
        return Docs._Filter(self.all_documents)


class ConsentForms:
    def __init__(self, all_documents):
        self.documents = Docs(all_documents).Filter.by_layout(["DOC Form"])


#### EOF
