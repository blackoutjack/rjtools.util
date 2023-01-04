
from util.convert import parse_numeric

def test_empty():
    val, _ = parse_numeric("")
    return val == 0

err_empty = "WARNING: No numeric data found: "

def test_basic():
    val, _ = parse_numeric("12")
    return val == 12

def test_fraction0():
    val, _ = parse_numeric("1/2")
    return val == 0.5

def test_fraction1():
    val, _ = parse_numeric("200 1/6")
    return val == 200 + (1/6)

def test_space_fraction():
    val, _ = parse_numeric("  10/11")
    return val == 10/11

def test_remaining0():
    val, rem = parse_numeric("21 engleberts ")
    return rem == "engleberts "

def test_remaining1():
    val, rem = parse_numeric("1 1/3 20")
    return val == 1 + (1/3) and rem == "20"

def test_remaining2():
    val, rem = parse_numeric("0g")
    return val == 0 and rem == "g"
