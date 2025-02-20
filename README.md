# dgutil python testing library

Python library containing various logging and testing utilities

## Requirements

* Python 3.12+

## Installation

To include `dgutils` in your project, add this line to `requirements.txt`

    -e git+https://github/blackoutjack/dgutil@0.1.0#egg=dgutil

The import in python code with

    import dgutils

## The `testing` framework

The `dgutil.testing` module implements a multithreaded test harness for python
modules. See the [`testing.py`](src/dgutil/testing.py) for documentation
explaining the usage.

