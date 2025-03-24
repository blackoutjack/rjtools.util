'''Test the type examination functionality in rjtools.util.type'''

from rjtools.util.msg import err
from rjtools.util.type import type_check, empty, nonempty

def test_basic():
    '''Test a basic type check for an integer'''
    i = 1
    type_check(i, int, "i")
    return True

def test_callable():
    '''Test the special case of checking for a callable'''
    def mydef(): pass
    type_check(mydef, callable, "mydef")
    return True

def test_list():
    """Test the special case of a list of types"""
    typ = [int, float]
    val = [5.2, 1, 5, 1.0]
    type_check(val, typ, "val")
    return True

def test_list_fail():
    """Test failure in the case of a list of types"""
    typ = [int, float]
    val = [1, "5.2", 2.0]
    try:
        type_check(val, typ, "val")
        return False
    except ValueError as ex:
        return True

def test_fail():
    '''Test a failing type check and the resulting error'''
    myvar = "string"
    try:
        type_check(myvar, int, "myvar") 
    except ValueError as ex:
        err("%s" % str(ex))
        return True
    return False

err_fail = "ERROR: Unexpected type for 'myvar': <class 'str'> (expected <class 'int'>)"

def test_can_be_none():
    myval = None
    type_check(myval, str, "myval", canBeNone=True)
    return True

def test_cannot_be_none():
    myval = None
    try:
        type_check(myval, str, "myval", canBeNone=False)
        return False
    except ValueError as ex:
        return True

def test_none_empty():
    val = None
    return empty(val)

def test_string_empty():
    val = ""
    return empty(val)

def test_array_empty():
    val = []
    return empty(val)

def test_dict_empty():
    val = {}
    return empty(val)

def test_string_nonempty():
    val = "a"
    return nonempty(val)

def test_array_nonempty():
    val = [None]
    return nonempty(val)

def test_dict_nonempty():
    val = {"a": None}
    return nonempty(val)




