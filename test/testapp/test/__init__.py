import sys
import os

sys.path.append("/home/rich/dev/rjtools.util/src")

from rjtools.util.testing import run_packages, run_modules, import_test_module

def run():
    mytest = import_test_module("mytest")
    badtest = import_test_module("badtest")

    return run_modules("testing.test.testapp", locals())
