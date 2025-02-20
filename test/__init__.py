
from src.dgutil.testing import init_mocks, run_modules
from src.dgutil import fs

from .testfs import files as mockfiles

def run():
    from . import convert
    from . import type_check
    from . import files
    from . import testing
    from . import log

    init_mocks(fs, mockfiles)

    return run_modules("util", locals())

