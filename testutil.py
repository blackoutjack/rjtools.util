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

def _get_test_url_map():
    try:
        urlMapString = os.getenv("TESTING_URL_MIRROR_MAP")
        if urlMapString is not None:
            urlMap = json.loads(urlMapString)
            return urlMap
    except json.JSONDecodeError:
        warn("Invalid JSON for testing URLs: %s" % os.getenv("TESTING_URL_MIRROR_MAP"))
    return None

def _is_mirrored_in(staticURL, urlMap):
    return urlMap is not None and staticURL in urlMap

def is_mirrored_for_test(staticURL):
    urlMap = _get_test_url_map()
    return _is_mirrored_in(staticURL, urlMap)

def load_mirror_url(staticURL):
    '''Replace the path with the temporary path that was created for testing.

    Works in conjunction with util.testing:initialize_dynamic_test_files, which
    creates the dynamic files and communicates the location via envvar.
    :param staticURL: string, path of the static file that was copied by the
        testing infrastructure
    :return: string, path of the dynamic file that can be modified during
        testing without changing the tracked static file
    '''

    if is_mirrored_for_test(staticURL):
        urlMap = _get_test_url_map()
        return urlMap[staticURL]
    else:
        return insert_suffix_into_filename(staticURL, ".mirror")

