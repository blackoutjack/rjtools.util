'''Test conversion functions in the util.convert module'''

from datetime import datetime
from util.convert import parse_date, parse_nonnumeric, parse_numeric, amount_to_grams

def test_numeric_empty():
    '''Test warning and 0 return value when input is the empty string'''
    val, _ = parse_numeric("")
    return val == 0

err_numeric_empty = "WARNING: No numeric data found: "

def test_numeric_basic():
    '''Test parsing of a simple integer'''
    val, _ = parse_numeric("12")
    return val == 12

def test_numeric_fraction0():
    '''Test a standalone fraction'''
    val, _ = parse_numeric("1/2")
    return val == 0.5

def test_numeric_fraction1():
    '''Test a number with a fraction'''
    val, _ = parse_numeric("200 1/6")
    return val == 200 + (1/6)

def test_numeric_space_fraction():
    '''Test a fraction preceded by whitespace'''
    val, _ = parse_numeric("  10/11")
    return val == 10/11

def test_numeric_remaining0():
    '''Test a whole number followed by whitespace and a string'''
    val, rem = parse_numeric("21 engleberts ")
    return rem == "engleberts "

def test_numeric_remaining1():
    '''Test a whole number and fraction followed by another number'''
    val, rem = parse_numeric("1 1/3 20")
    return val == 1 + (1/3) and rem == "20"

def test_numeric_remaining2():
    '''Test a simple number and unit string'''
    val, rem = parse_numeric("0g")
    return val == 0 and rem == "g"

def test_nonnumeric_empty():
    '''Test the parsed and remaining strings are empty for empty input'''
    val, rem = parse_nonnumeric("")
    return val == "" and rem == ""

def test_nonnumeric_basic():
    '''Test a basic case for parse_nonnumeric'''
    val, _ = parse_nonnumeric("abc 12")
    return val == "abc"

def test_nonnumeric_space():
    '''Test that whitespace is stripped from the parsed value'''
    val, _ = parse_nonnumeric("  xyz ")
    return val == "xyz"

def test_nonnumeric_remaining0():
    '''Test the parsed and remaining string for a string with whitespace'''
    val, rem = parse_nonnumeric(" engleberts 21 ")
    return val == "engleberts" and rem == " 21 "

def test_nonnumeric_remaining1():
    '''Test the parsed and remaining string when a digit is in a word'''
    val, rem = parse_nonnumeric("g0g")
    return val == "g" and rem == "0g"

def test_date_empty():
    '''Test exception thrown when the empty string is given to parse_date'''
    try:
        parse_date("")
    except ValueError:
        return True
    return False

def test_date_basic():
    '''Test basic date parsing'''
    date = parse_date("1/1/2023")
    return date.strftime("%Y-%m-%d") == "2023-01-01"

def test_amount_to_grams_empty():
    '''Test warning and 0 return value when input is the empty string'''
    val = amount_to_grams("")
    return val == 0

err_amount_to_grams_empty = "WARNING: No amount specified"


