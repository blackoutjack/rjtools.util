
from rjtools.util.collection import flatmap

def test_flatmap_basic():
    flattened = flatmap(lambda x: x, [[1,2],[3,4],[5,6]])
    return flattened == [1,2,3,4,5,6]
