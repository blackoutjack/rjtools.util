"""
Data types and schema class for constructing a database wrapper
"""
import os
import ast

from .type import type_check
from .msg import dbg

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

class SchemaLoadError(Exception):
    def __init__(self, msg, fileName=None):
        message = "Unable to load schema"
        if fileName is not None:
            message += f" from file {fileName}"
        message += f": {msg}"
        super().__init__(message)

class DisallowedConstructError(SchemaLoadError):
    def __init__(self, constructName, fileName=None):
        message = f"Disallowed code {constructName}"
        if fileName is not None:
            message += f" in file {fileName}"
        super().__init__(message)


def validate_schema_definition(unsafeCode, fileToReport=None):
    """
    Walks the given code's ast and errors if unallowed constructs are found

    :param unsafeCode: code the needs to be validated
    :param fileToReport: filename to use in error messages
    :raises: SchemaLoadError, DisallowedConstructError
    :return: code that has been deemed safe by the validation
    :rtype: str
    """
    allowedNodeTypes = (ast.Module, ast.Assign, ast.Name, ast.Constant,
        ast.Store, ast.Dict, ast.Load, ast.List, ast.Tuple)
    try:
        mod = ast.parse(unsafeCode)
    except BaseException as ex:
        raise SchemaLoadError(str(ex), fileToReport)

    for node in ast.walk(mod):
        if isinstance(node, ast.Call):
            if node.func.id != "TableSchema" or len(node.args) > 4:
                raise DisallowedConstructError(
                    "ast.Call to function other than `TableSchema`",
                    fileToReport)
        elif isinstance(node, ast.Attribute):
            if (node.value.id != "DataType"
                or node.attr not in DataType.__members__.keys()):
                raise DisallowedConstructError(
                    "ast.Attribute access other than DataType",
                    fileToReport)
        elif not isinstance(node, allowedNodeTypes):
            raise DisallowedConstructError(type(node), fileToReport)
    safeCode = unsafeCode # Now that it has been validated.
    return safeCode

def load_schema_from_file(filePath):
    """
    Eval a Python file to generate a TableSchema object.

    :param filePath: str, file that initializes the `TableSchema`
    :raises: DisallowedConstructError, SchemaLoadError
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
        "__builtins__": {},
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


def load_schemas_from_dir(schemaDir):
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

