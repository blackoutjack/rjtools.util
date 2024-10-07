'''Functions to be called from applications to help support testing

These utilities are not contained in util.testing since that would potentially
cause a circular dependency.
'''
import os
import json
import traceback
import random

from util.msg import warn, dbg

def get_test_token():
    return "%d" % random.randrange(10000000)

# Wrap expected output in this class to search for the term in the output rather
# than matching the entire string.
class Grep:
    def __init__(self, search):
        # String to search for
        self.search = search

def load_test_filepath(staticFile):
    '''Replace the path with the temporary path that was created for testing.

    Works in conjunction with util.testing:initialize_dynamic_test_files, which
    creates the dynamic files and communicates the location via envvar.
    :param staticFile: string, path of the static file that was copied by the
        testing infrastructure
    :return: string, path of the dynamic file that can be modified during
        testing without changing the tracked static file
    '''
    filemap = {}
    try:
        filestring = os.getenv("TESTING_FILES")
        if filestring is not None:
            filemap = json.loads(filestring)
    except json.JSONDecodeError:
        warn("Invalid JSON for testing files: %s" % os.getenv("TESTING_FILES"))

    if staticFile in filemap:
        return filemap[staticFile]
    else:
        return staticFile

