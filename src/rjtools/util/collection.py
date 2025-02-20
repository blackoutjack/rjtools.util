"""Utility functions for working with collection types."""


def update_multimap(multimap:dict, key, value):
    """
    Add a value to a multimap

    :param multimap: the multimap to update
    :param key: key in the multimap
    :param value: value to add for the key
    :return: bool, whether a value was already present for the key
    """
    if key not in multimap:
        multimap[key] = []
    values = multimap[key]
    foundDuplicate = len(values) > 0
    values.append(value)
    return foundDuplicate
