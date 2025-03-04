from rjtools.util.testing import run_packages, import_test_module

def run():
    mocked = import_test_module("unit")
    e2e = import_test_module("e2e")

    return run_packages("rjtools.util", locals())

