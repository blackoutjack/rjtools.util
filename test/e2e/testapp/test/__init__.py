
from rjtools.util.testing import run_modules, import_test_module

def run():
    mytest = import_test_module("mytest")
    badtest = import_test_module("badtest")

    return run_modules("testing.test.e2e.testapp", locals())
