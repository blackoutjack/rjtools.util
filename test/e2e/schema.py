import os

from rjtools.util.schema import (TableSchema, DisallowedConstructError,
    SchemaLoadError, load_schema_from_file, load_schemas_from_dir)

TEST_DIR = os.path.dirname(__file__)

def test_load_schema_basic():
    schema = load_schema_from_file(os.path.join(TEST_DIR, "schemas/rainfall.py"))
    return isinstance(schema, TableSchema)

def test_load_schema_problem():
    schema = load_schema_from_file(os.path.join(TEST_DIR, "schemas-bad/rainfall.py"))
    return isinstance(schema, TableSchema)

out_load_schema_problem = "Exception occurred during schema/test_load_schema_problem: SchemaLoadError: Unable to load schema: name 'Date' is not defined"

result_load_schema_problem = None

def test_try_load_schema_bad_syntax():
    try:
        load_schema_from_file(
            os.path.join(TEST_DIR, "schemas-bad/badsyntax.py"))
        return False
    except SchemaLoadError:
        return True

def test_try_load_schema_file_not_found():
    try:
        load_schema_from_file(
            os.path.join(TEST_DIR, "schemas/filenotfound.py"))
        return False
    except SchemaLoadError:
        return True

def test_try_load_schema_disallowed_syntax():
    try:
        load_schema_from_file(
            os.path.join(TEST_DIR, "schemas-bad/disallowedsyntax.py"))
        return False
    except DisallowedConstructError:
        return True

def test_try_load_schemas_from_dir():
    schemas = load_schemas_from_dir(os.path.join(TEST_DIR, "schemas"))
    return all([isinstance(s, TableSchema) for s in schemas.values()])

