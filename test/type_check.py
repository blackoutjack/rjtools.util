
from util.type import type_check

def test_basic():
    i = 1
    type_check(i, int, "i")
    return True

def test_callable():
    def mydef(): pass
    type_check(mydef, callable, "mydef")
    return True

