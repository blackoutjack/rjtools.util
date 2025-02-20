'''Functions to be called from applications to help support testing

These utilities are not contained in util.testing since that would potentially
cause a circular dependency.
'''
import json
import random


def get_test_token():
    """
    Get a pseudo-random token to test data flowing in and out of storage

    :return: a pseudo-random token
    :rtype: str
    """
    return "%d" % random.randrange(10000000)

class Link:
    """
    Represents a symlink within a mock filesystem
    """
    def __init__(self, target):
        self.target = target

class Grep:
    """
    Wrap expected output in this class to search for the term in the output
    rather than matching the entire string.
    """

    def __init__(self, search):
        # String to search for
        self.search = search


class JSONFilter:
    """
    Filter JSON output by removing certain keys
    """

    def __init__(self, remove, text):
        # JSON attributes to remove
        self.remove = remove
        self.text = text.strip()

    def applyFilter(self, output):
        jsonObj = json.loads(output)
        filteredObj = filterJSONRecursive(jsonObj, self.remove)
        return json.dumps(filteredObj, indent=2)


def filterJSONRecursive(jsonObj, keysToRemove):
    """
    Recursively remove keys from a JSON object
    """
    if isinstance(jsonObj, dict):
        for key in keysToRemove:
            if key in jsonObj:
                del jsonObj[key]
        for key, value in jsonObj.items():
            jsonObj[key] = filterJSONRecursive(value, keysToRemove)
    elif isinstance(jsonObj, list):
        for i, subObj in enumerate(jsonObj):
            jsonObj[i] = filterJSONRecursive(subObj, keysToRemove)
    return jsonObj
