
from util.testing import init_stubs, run_tests
from util import fs

def run():
    from . import convert
    from . import type_check
    from . import files
    from . import testing

    init_stubs(fs)

    return run_tests(dir(), locals(), "util")

