import sys

from util.testing import init_testing, run_tests

def test():
    from . import parse_date
    from . import parse_numeric
    from . import parse_nonnumeric
    from . import amount_to_grams
    from . import type_check

    return run_tests(dir(), locals())

if __name__ == "__main__":
    init_testing()
    sys.exit(test())
