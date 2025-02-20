
from dgutil.testing import init_stubs, run_modules
from dgutil import fs

def run():
    from . import convert
    from . import type_check
    from . import files
    from . import testing
    from . import log

    init_stubs(fs)

    return run_modules("util", locals())

