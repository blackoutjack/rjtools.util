
from util.convert import parse_nonnumeric

def test_empty():
    val, rem = parse_nonnumeric("")
    return val == "" and rem == ""

def test_basic():
    val, _ = parse_nonnumeric("abc 12")
    return val == "abc"

def test_space():
    val, _ = parse_nonnumeric("  xyz ")
    return val == "xyz"

def test_remaining0():
    val, rem = parse_nonnumeric(" engleberts 21 ")
    return val == "engleberts" and rem == " 21 "

def test_remaining1():
    val, rem = parse_nonnumeric("g0g")
    return val == "g" and rem == "0g"
