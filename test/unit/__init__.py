
from rjtools.util.testing import run_modules, import_test_module
from rjtools.util import fs

from .testfs import files as mockfiles

def run():
    convert = import_test_module("convert")
    type_check = import_test_module("type_check")
    files = import_test_module("files")
    log = import_test_module("log")

    fs.install_mocks(mockfiles)

    return run_modules("rjtools.util", locals())

