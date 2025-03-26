"""Utility functions for working with collection types."""

from collections.abc import Callable
from functools import reduce

def update_multimap[K,V](
    multimap:dict[K,list[V]],
    key:K, value:V) -> bool:
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

def flatmap[T,U](
        func:Callable[[T],list[U]],
        coll:list[T]
    ) -> list[U]:
    """
    Functional flatmap operation

    Flatten a list of lists into a list with one level less nesting.
    """
    return reduce(lambda accum, next: accum + func(next), coll, [])

