"""
Data types and schema class for constructing a database wrapper
"""
import os
import ast
from typing import Optional, Union, Any, cast

from .type import type_check
from .msg import dbg

from enum import Flag, auto


class DataType(Flag):
    AUTOID = auto()
    FORMULA = auto()
    DATE = auto()
    INT = auto()
    STRING = auto()
    TEXT = auto()
    DATETIME = auto()
    TIMESTAMP = auto()
    CREATETIMESTAMP = auto()
    AUTOTIMESTAMP = auto()


class TableSchema:
  def __init__(
      self, name:str,
      columnDefs:dict[str,DataType],
      keyNames:Union[str,tuple[str]],
      indexes:list[Union[str,tuple[str]]]=[],
      extra:dict[str, Any]={},
      headerRowNum:int=1,
      foreignKeys:Optional[dict[str,str]]=None):
        self.name = name
        self.columns = list(columnDefs.keys())
        self.columnTypes = columnDefs
        self.key = keyNames
        self.indexes = indexes
        self.header_row_num = headerRowNum
        self.foreign_keys = foreignKeys
        for propName in extra.keys():
            if hasattr(self, propName):
                raise ValueError(
                    f"Cannot overwrite property {propName} in schema {name}")
            setattr(self, propName, extra[propName])

class SchemaLoadError(Exception):
    def __init__(self, msg:str, fileName:Optional[str]=None):
        message = "Unable to load schema"
        if fileName is not None:
            message += f" from file {fileName}"
        message += f": {msg}"
        super().__init__(message)

class DisallowedConstructError(SchemaLoadError):
    def __init__(self, constructName:Any, fileName:Optional[str]=None):
        message = f"Disallowed code {constructName}"
        if fileName is not None:
            message += f" in file {fileName}"
        super().__init__(message)


def validate_schema_definition(unsafeCode:str, fileToReport:Optional[str]=None) -> str:
    """
    Walks the given code's ast and errors if unallowed constructs are found

    :param unsafeCode: code the needs to be validated
    :param fileToReport: filename to use in error messages
    :raises: SchemaLoadError, DisallowedConstructError
    :return: code that has been deemed safe by the validation
    :rtype: str
    """
    allowedNodeTypes = (ast.Module, ast.Assign, ast.Name, ast.Constant,
        ast.Store, ast.Dict, ast.Load, ast.List, ast.Tuple, ast.keyword)
    try:
        mod = ast.parse(unsafeCode)
    except BaseException as ex:
        raise SchemaLoadError(str(ex), fileToReport)

    for node in ast.walk(mod):
        if isinstance(node, ast.Call):
            argCnt = len(node.args)
            if isinstance(node.func, ast.Name):
                if node.func.id == "TableSchema" and argCnt > 2 and argCnt < 7:
                    # Allow the `TableSchema` constructor to be called.
                    pass
                elif isinstance(node.func, ast.Name) and node.func.id == "locals" and argCnt == 0:
                    # Allow `locals()` to be called to set up property names.
                    pass
                else:
                    raise DisallowedConstructError(
                        f"ast.Call to disallowed function {node.func.id}",
                        fileToReport)
            else:
                raise DisallowedConstructError(
                    f"ast.Disallowed function call {node.func}",
                    fileToReport)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if (node.value.id != "DataType"):
                    raise DisallowedConstructError(
                        f"ast.Attribute access other than DataType: {node.value.id}",
                        fileToReport)
                if (node.attr not in DataType.__members__.keys()):
                    raise DisallowedConstructError(
                        f"ast.Attribute access to non-member of DataType: {node.attr}",
                        fileToReport)
            else:
                raise DisallowedConstructError(
                    f"ast.Attribute access of unnamed reference: {node.attr}",
                    fileToReport)
        elif not isinstance(node, allowedNodeTypes):
            raise DisallowedConstructError(type(node), fileToReport)
    safeCode = unsafeCode # Now that it has been validated.
    return safeCode

def load_schema_from_file(filePath:str) -> TableSchema:
    """
    Eval a Python file to generate a TableSchema object.

    :param filePath: str, file that initializes the `TableSchema`
    :raises: SchemaLoadError
    :return: the generated schema object
    :rtype: TableSchema

    Syntax within the file is limited to constructs used in the following
    example. Builtins are not available, calls are only allowed to
    `TableSchema` and property accesses are restricted to `DataType`. The
    schema must be assigned to a variable named `schema`.

        NAME = "Rainfall"

        ID = "Id"
        DATE = "Date"
        AMOUNT = "Amount"

        KEY = ID

        schema = TableSchema(
            NAME,
            {
                ID: DataType.AUTOID,
                DATE: DataType.DATE,
                AMOUNT: DataType.STRING,
            }
            KEY,
            [DATE],
            locals(), # To set `NAME`, `ID`, etc. as properties on the object.
        )
    """
    type_check(filePath, str, "filePath")

    try:
        fl = open(filePath, 'rt', encoding='utf-8')
    except OSError as ex:
        raise SchemaLoadError(str(ex), filePath)
    unsafeCode = "".join(fl.readlines())
    safeCode = validate_schema_definition(unsafeCode, filePath)

    globals = {
        "__builtins__": {"locals": locals},
        "TableSchema": TableSchema,
        "DataType": DataType,
        "schema": None
    }

    try:
        exec(safeCode, globals)
    except BaseException as ex:
        raise SchemaLoadError(str(ex))
    schema = globals["schema"]

    return schema


def load_schemas_from_dir(schemaDir:str) -> dict[str, TableSchema]:
    """
    Scans a directory and attempts to load any .py file as a TableSchema.

    Restricted syntax is enforced, and errors in any file results in an error
    for the entire directory. If you want the schemas that were loaded
    successfully even if errors occurred in some, then call
    `load_schema_from_file` directly.

    :param schemaDir: directory containing the schema files
    :raises: SchemaLoadError
    :return: map of table names to schemas found in the directory
    :rtype: map of str => TableSchema
    """
    type_check(schemaDir, str, "schemaDir")

    schemas = {}
    for fileName in os.listdir(schemaDir):
        if not fileName.endswith(".py"):
            dbg(f"Skipping non-Python file {fileName} in schema directory {schemaDir}")
            continue

        filePath = os.path.join(schemaDir, fileName)
        schema = load_schema_from_file(filePath)

        if isinstance(schema, TableSchema):
            schemas[schema.name] = schema
        else:
            raise SchemaLoadError(f"Unexpected value produced when loading schema {filePath}: {schema}")
    return schemas

