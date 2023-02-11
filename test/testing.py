'''Test the behaviors of the util.testing module

These tests should not call util.testing functions directly since that would
be a cyclic dependency. Rather, write tests that demonstrate the testing module
is working correctly when it executes them.'''


value_for_order_test = 0

def test_order_first():
    '''With test_next_order, ensure that tests are run in order of definition'''
    global value_for_order_test
    value_for_order_test = 1
    return True

def test_next_order():
    '''Alphabetically before test_order_first but should be executed second'''
    return value_for_order_test == 1

def test_exception():
    '''Cause an exception during the test to ensure reasonable handling'''
    mymap = {}
    print("some normal output")
    print("whoops: %s" % mymap["missing"])

out_exception = "some normal output"

err_exception = '''
Exception occurred during util.test.testing/test_exception: KeyError: 'missing'
'''

result_exception = None
