"""Utility functions for type-checking"""

from typing import Any, TypeGuard

def empty(value:Any) -> bool:
    """
    Emptiness check, polymorphic over None, str and list

    :param value: value to check for emptiness
    :return: whether the value is empty
    :rtype: bool
    """
    return value in [None, '', [], {}]

def nonempty[T](value:T|None) -> TypeGuard[T]:
    """Non-emptiness check, inverse of `empty`

    :param value: value to check for emptiness
    :return: whether the value is empty
    :rtype: bool
    """
    return not empty(value)

def type_error(varname, actual_typename, expected_typename):
    """Raise ValueError with standardized message for type-check failures

    ValueError, not TypeError, just because I prefer to catch just one type.

    :param varname: str, variable or expression that failed a type check
    :param actual_typename: str, name of the expression's actual type
    :param expected_typename: str, name of the expected type
    :raises: ValueError
    """

    raise ValueError("Unexpected type for '%s': %s (expected %s)"
            % (varname, actual_typename, expected_typename))

def has_type(val, typ):
    """
    Slightly enhanced version of `isinstance`

    :param val: value whose type to check
    :param typ: type to check for
    """
    if typ == callable:
        # Special case: check if `val` is "callable" (not technically a type)
        return callable(val)
    if typ is None:
        return val is None
    return isinstance(val, typ)

def type_check(val, typ, varname, canBeNone=False):
    """
    Verify that `val` has type `typ`, or raise a ValueError

    :param val: value whose type to check
    :param typ: type|list, a type value will simply check for that type, while
        a list containing type values checks that the value is a list
        containing values of only those types. An empty list just check that
        the value is a list.
    :param varname: name of the variable (or any expr.) to include in errors
    :param canBeNone: whether `None` is an acceptable value for `val`
    """
    if canBeNone and val is None: return

    if isinstance(typ, list):
        # Check that `val` is a list of values with the type that `typ` contains
        if not has_type(val, list):
            type_error(varname, str(type(val)), "list")

        if len(typ) == 0:
            return

        for index, subval in enumerate(val):
            ok = any([has_type(subval, t) for t in typ])

            if not ok: type_error(
                "%s[%d]" % (varname, index),
                str(type(subval)),
                " or ".join([str(t) for t in typ]))

    elif not has_type(val, typ):
        type_error(varname, str(type(val)), str(typ))

