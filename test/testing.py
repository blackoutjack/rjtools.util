'''Test the behaviors of the rjtools.util.testing module

These tests should not call rjtools.util.testing functions directly since that would
be a cyclic dependency. Rather, write tests that demonstrate the testing module
is working correctly when it executes them.'''


value_for_order_test = 0

def test_order_first():
    '''With test_next_order, ensure that tests are run in order of definition'''
    global value_for_order_test
    initialValue = value_for_order_test
    value_for_order_test = 1
    return initialValue == 0

def test_next_order():
    '''Alphabetically before test_order_first but should be executed second'''
    return value_for_order_test == 1


def test_exception():
    '''Cause an exception during the test to ensure reasonable handling'''
    mymap = {}
    print("some normal output")
    print("whoops: %s" % mymap["missing"])

out_exception = '''
some normal output
Exception occurred during test.testing/test_exception: KeyError: 'missing'
'''

result_exception = None


"""Run a subprocess test (prefixed by "run_") check output."""
run_basic_subprocess = ["echo", "this should be the output"]

out_basic_subprocess = "this should be the output"


# For the following tests, set the command accepting batch input.
run_basic_stdin = ["cat"]

"""Send batch input (prefixed by "batch_") check output."""
in_basic_stdin = '''
here is some content
may it serve you well
'''

out_basic_stdin = '''
here is some content
may it serve you well
'''

run_failure_stdin = ["grep", "stringnotfound"]

in_failure_stdin = '''
input without the grepped-for string
'''

code_failure_stdin = 1

