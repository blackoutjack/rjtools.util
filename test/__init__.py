
from util.testing import init_stubs, run_modules
from util import fs

def run():
    from . import convert
    from . import type_check
    from . import files
    from . import testing
    from . import log

    init_stubs(fs)

    return run_modules("util", locals())

