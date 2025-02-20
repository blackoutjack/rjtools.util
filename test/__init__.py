
from src.dgutil.testing import run_modules
from src.dgutil import fs

from .testfs import files as mockfiles

def run():
    from . import convert
    from . import type_check
    from . import files
    from . import testing
    from . import log

    fs.install_mocks(mockfiles)

    return run_modules("util", locals())

