# rjtools.util: a multithreaded Python testing library

Python library containing various logging and testing utilities

## Requirements

* Python 3.12+

## Installation

To include `rjtools.util` in your project, add this line to `requirements.txt`

    -e git+https://github/blackoutjack/rjtools.util@0.0.1#egg=util

## The `testing` framework

The `rjtools.util.testing` module implements a multithreaded test harness for python
modules. See the [`testing.py`](src/rjtools/util/testing.py) for documentation
explaining the usage.

A prototypical test suite will include a structure like the following
```
<project>/test/
├── __init__.py
├── __main__.py
├── testmodule1.py
└── another_test_module.py
```

The `__init__.py` must contain a `run` function that imports the desired test
modules and passes them to `rjtools.util.testing.run_modules`.

``` py title="test/__init__.py"
from rjtools.util.testing import run_modules

def run():
    from . import testmodule1
    from . import another_test_module

    return run_modules("<project>", locals())
```

An example test module could include the following, in which the `run_`
prefix specifies a command to run as a subprocess, and the matching
module property starting with `out_` specifies the expected output on `stdout`.

``` py title="testmodule1.py"
# Basic test launching a subprocess with these args.
run_basic_test = ["python", "-m", "<project>", "-o", "arg"]

# The expected output produced by the subprocess.
out_basic_test = '''
<project> ran successfully,
and produced this output
'''
```

A test fails if the output does not match (module 1 line break before or after)
and similar checks are done based on any `err_`.

Other capabilities including support for unit testing are also included in the
library.
