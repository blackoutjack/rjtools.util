
from rjtools.util.testing import run_modules, import_test_module

def run():

    schema = import_test_module("schema")
    testing = import_test_module("testing")

    return run_modules("rjtools.util", locals())

