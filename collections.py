#
# Utility functions for working with collection types.
#

def update_multimap(multimap, key, value):
    foundDuplicate = False
    if key not in multimap:
        multimap[key] = []
    values = multimap[key]
    foundDuplicate = len(values) > 0
    values.append(value)
    return foundDuplicate
