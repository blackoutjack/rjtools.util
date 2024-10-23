'''Functions to be called from applications to help support testing

These utilities are not contained in util.testing since that would potentially
cause a circular dependency.
'''
import os
import json
import traceback
import random

from util.msg import warn, dbg
from util.file import insert_suffix_into_filename

def get_test_token():
    return "%d" % random.randrange(10000000)

# Wrap expected output in this class to search for the term in the output rather
# than matching the entire string.
class Grep:
    def __init__(self, search):
        # String to search for
        self.search = search


