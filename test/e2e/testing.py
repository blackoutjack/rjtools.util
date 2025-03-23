'''Test the behaviors of the rjtools.util.testing module

These tests should not call rjtools.util.testing functions directly since that would
be a cyclic dependency. Rather, write tests that demonstrate the testing module
is working correctly when it executes them.'''

from rjtools.util.testutil import Grep

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
Exception occurred during testing/test_exception: KeyError: 'missing'
'''

result_exception = None


"""Run a subprocess test (prefixed by "run_") check output."""
run_basic_subprocess = ["echo", "this should be the output"]

out_basic_subprocess = "this should be the output"

"""Run a subprocess test (prefixed by "run_") check output."""
run_subprocess_with_ints = ["echo", 1, 2, 3]

out_subprocess_with_ints = "1 2 3"

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


run_testsuite_pass = ["python3", "-m", "test.e2e.testapp.testpass"]

out_testsuite_pass = """
testing.test.e2e.testapp: running tests
testing.test.e2e.testapp/mytest.run_ok_one: pass
testing.test.e2e.testapp/mytest.run_ok_two: pass
testing.test.e2e.testapp: ran 2 tests, all successful
"""

code_testsuite_pass = 0


run_testsuite_fail = ["python3", "-m", "test.e2e.testapp.testfail"]

out_testsuite_fail = Grep("""testing.test.e2e.testapp: running tests
testing.test.e2e.testapp/mytest.run_ok_function: pass""", """
testing.test.e2e.testapp/mytest.run_buggy_function: FAIL""")

code_testsuite_fail = 1


run_testsuite_result_warning = ["python3", "-m", "test.e2e.testapp.testwarn"]

out_testsuite_result_warning = Grep(
    """testing.test.e2e.testapp/mytest.run_ok_function: pass""")

err_testsuite_result_warning = """
WARNING: no results returned by the main testsuite module
"""

code_testsuite_result_warning = 1


run_testsuite_bad_run = ["python3", "-m", "test.e2e.testapp.testbadrun"]

out_testsuite_bad_run = Grep(
    "testing.test.e2e.testapp/badtest.run_ok: pass",
    "testing.test.e2e.testapp/badtest.run_bad: FAIL")

code_testsuite_bad_run = 1


run_testsuite_bad_test = ["python3", "-m", "test.e2e.testapp.testbadtest"]

out_testsuite_bad_test = Grep(
    "testing.test.e2e.testapp/badtest.test_ok: pass",
    "testing.test.e2e.testapp/badtest.test_bad: FAIL")

code_testsuite_bad_test = 1


run_testsuite_bad_module = ["python3", "-m", "test.e2e.testapp.testbadmod"]

out_testsuite_bad_module = Grep(
"""ERROR: Detected syntax error in badmodule: invalid syntax \\(badmodule.py, line 3\\)
testing.test.e2e.testapp: running tests
testing.test.e2e.testapp/mytest.run_ok_function: pass""")

code_testsuite_bad_module = 1


def test_simple_test():
    return True

def test_sys_exit():
    import sys
    sys.exit()

result_sys_exit = None

out_sys_exit = "Exception occurred during testing/test_sys_exit: SystemExit: "

