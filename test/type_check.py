
from util.msg import err
from util.type import type_check

def test_basic():
    i = 1
    type_check(i, int, "i")
    return True

def test_callable():
    def mydef(): pass
    type_check(mydef, callable, "mydef")
    return True

def test_fail():
    myvar = "string"
    try:
        type_check(myvar, int, "myvar") 
    except ValueError as ex:
        err("%s" % str(ex))
        return True
    return False

err_fail = "ERROR: Unexpected type for 'myvar': <class 'str'> (expected <class 'int'>)"


