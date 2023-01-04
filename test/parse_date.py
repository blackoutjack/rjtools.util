
import numpy
from util.convert import parse_date

def test_empty():
    try:
        parse_date("")
    except Exception as ex:
        return True
    return False

def test_basic():
    date = parse_date("1/1/2023")
    return date == numpy.datetime64("2023-01-01")

