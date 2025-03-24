"""Utility functions for working with collection types."""

from collections.abc import Callable
from functools import reduce
from typing import TypeVar




def update_multimap(multimap:dict[TypeVar("T")], key:str, value:TypeVar("T")):
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

def flatmap(func:Callable[[TypeVar("T")],list], coll:list[TypeVar("T")]):
    return reduce(lambda accum, next: accum + func(next), coll, [])

