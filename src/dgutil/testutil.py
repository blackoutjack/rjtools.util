'''Functions to be called from applications to help support testing

These utilities are not contained in util.testing since that would potentially
cause a circular dependency.
'''
import os
import json
import traceback
import random

from dgutil.msg import warn, dbg
from dgutil.file import insert_suffix_into_filename

def get_test_token():
    return "%d" % random.randrange(10000000)

# Wrap expected output in this class to search for the term in the output rather
# than matching the entire string.
class Grep:
    def __init__(self, search):
        # String to search for
        self.search = search

class JSONFilter:
    def __init__(self, remove, text):
        # JSON attributes to remove
        self.remove = remove
        self.text = text.strip()

    def applyFilter(self, output):
        jsonObj = json.loads(output)
        filteredObj = filterJSONRecursive(jsonObj, self.remove)
        return json.dumps(filteredObj, indent=2)


def filterJSONRecursive(jsonObj, keysToRemove):
    if isinstance(jsonObj, dict):
        for key in keysToRemove:
            if key in jsonObj:
                del jsonObj[key]
        for key, value in jsonObj.items():
            jsonObj[key] = filterJSONRecursive(value, keysToRemove)
    elif isinstance(jsonObj, list):
        for i in range(len(jsonObj)):
            jsonObj[i] = filterJSONRecursive(jsonObj[i], keysToRemove)
    return jsonObj

