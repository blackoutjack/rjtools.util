
from util.convert import amount_to_grams

def test_empty():
    val = amount_to_grams("")
    return val == 0

err_empty = "WARNING: No amount specified"
