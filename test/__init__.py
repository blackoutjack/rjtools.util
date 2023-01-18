
from util.testing import init_stubs, run_tests
from util import fs

def run():
    from . import parse_date
    from . import parse_numeric
    from . import parse_nonnumeric
    from . import amount_to_grams
    from . import type_check
    from . import files

    init_stubs(fs)

    return run_tests(dir(), locals(), "util")

