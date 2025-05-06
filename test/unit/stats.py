from rjtools.util.stats import get_median_of_sorted, get_modes_of_sorted

def test_median_basic():
    vals = [1, 4, 5]
    median = get_median_of_sorted(vals)
    return median == 4

def test_median_even():
    vals = [1, 4]
    median = get_median_of_sorted(vals)
    return median == 2.5

def test_median_empty():
    vals = []
    median = get_median_of_sorted(vals)
    return median is None

def test_mode_basic():
    vals = [0, 0, 1, 4, 5, 6, 6, 6, 7]
    mode = get_modes_of_sorted(vals)
    return mode == [6]

def test_mode_empty():
    vals = []
    mode = get_modes_of_sorted(vals)
    return mode is None

def test_mode_multiple():
    vals = [0, 0, 1, 2, 2, 4, 5, 6, 6]
    modes = get_modes_of_sorted(vals)
    return modes == [0, 2, 6]
