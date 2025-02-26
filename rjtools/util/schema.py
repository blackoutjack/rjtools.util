"""
Data types and schema class for constructing a database wrapper
"""

from enum import Flag, auto


class DataType(Flag):
    AUTOID = auto()
    FORMULA = auto()
    DATE = auto()
    STRING = auto()
    TEXT = auto()
    DATETIME = auto()
    TIMESTAMP = auto()
    CREATETIMESTAMP = auto()
    AUTOTIMESTAMP = auto()


class TableSchema:
    def __init__(self, name, columnDefs, keyNames, indexes=[], headerRowNum=1):
        self.name = name
        self.columns = list(columnDefs.keys())
        self.columnTypes = columnDefs
        self.key = keyNames
        self.indexes = indexes
        self.header_row_num = headerRowNum
