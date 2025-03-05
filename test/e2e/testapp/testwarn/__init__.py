
from rjtools.util.testing import run_modules, import_test_module

def run():
    mytest = import_test_module("mytest")

    # %%% Intentionally not returning the results from run_modules to test
    # %%% the warning in such a case.
    run_modules("testing.test.e2e.testapp", locals())
