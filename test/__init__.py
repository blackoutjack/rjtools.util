
from src.rjtools.util.testing import run_modules
from src.rjtools.util import fs

from .testfs import files as mockfiles

def run():
    from . import convert
    from . import type_check
    from . import files
    from . import testing
    from . import log

    fs.install_mocks(mockfiles)

    return run_modules("rjtools.util", locals())

