
from rjtools.util.testing import run_modules, import_test_module

def run():

    testing = import_test_module("testing")

    return run_modules("rjtools.util", locals())

