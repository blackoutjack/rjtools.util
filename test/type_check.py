'''Test the type examination functionality in util.type'''

from src.dgutil.msg import err
from src.dgutil.type import type_check

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


