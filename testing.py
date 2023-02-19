'''Utility functions and classes to support automated testing'''

import sys
import os
import shutil
import subprocess
import traceback
from threading import Thread, Condition, RLock
from io import TextIOWrapper, BytesIO
from optparse import OptionParser

from util.msg import set_debug, get_debug, dbg, info, warn, err, s_if_plural
from util.type import type_check

# Toggle parallel running of test modules. Test cases within a module are
# always run in the order they are defined in the module.
MULTITHREADED = False

# Prefixes of symbol names to use for defining test cases in a test module.
# Symbols matching these prefixes are taken up as test cases.
INPROCESS_TEST_PREFIX = "test_"
SUBPROCESS_TEST_PREFIX = "run_"
BATCH_TEST_PREFIX = "batch_"

# Prefixes of symbol names for defining expected output for test cases.
INPROCESS_RESULT_PREFIX = "result_"
SUBPROCESS_CODE_PREFIX = "code_"
TEST_OUTPUT_PREFIX = "out_"
TEST_ERROR_PREFIX = "err_"

# Thread
redirect = None
# Thread lock for coordinating
redirect_lock = RLock()

class TestResults:
    def __init__(self, suiteName):
        self.name = suiteName
        self.code = 0
        self.total = 0
        self.failures = 0

    def add_success(self):
        self.total += 1

    def add_failure(self):
        self.code = 1
        self.total += 1
        self.failures += 1

    def print(self):
        # Producing output needs the lock to ensure redirection isn't in effect
        redirect_lock.acquire()
        initial = "%s: ran %d test%s" % (
                self.name,
                self.total,
                s_if_plural(self.total)
            )
        if self.failures > 0:
            warn("%s, %d failure%s"
                % (initial, self.failures, s_if_plural(self.failures)))
        else:
            print("%s, all successful" % initial)
        redirect_lock.release()

# Wrap expected output in this class to search for the term in the output rather
# than matching the entire string.
class Grep:
    def __init__(self, search):
        # String to search for
        self.search = search

def summarize_results(name, *results):
    '''Produce a summary TestResults object from the given results
    
    :param name: a descriptive name for the summary results
    :param results: TestResults objects to be summarized
    :return: a summary TestResults object
    '''
    summary = TestResults(name)
    summary.total = sum([result.total for result in results])
    summary.failures = sum([result.failures for result in results])
    summary.code = max([result.code for result in results])
    return summary

def cull_debug_lines(lines, std):
    '''Remove lines formatted like debug output, and print them to a stream

    Allows tests to run with -g without false failures due to extraneous output.
    :param lines: lines of output
    :param std: output stream to print the culled debug text
    :return: the text without debug content concatenated into a string
    '''
    out = ""
    for line in lines:
        if line.startswith("DEBUG: "):
            print(line, file=std, end='')
        else:
            out += line
    return out

def cull_debug_text(text, std):
    '''Remove text formatted like debug output, and print it to a stream

    Allows tests to run with -g without false failures due to extraneous output.
    :param lines: a string of text
    :param std: output stream to print the culled debug text
    :return: the text without debug content
    '''
    lines = text.splitlines(keepends=True)
    return cull_debug_lines(lines, std)

class Redirect(TextIOWrapper):
    "Manages the redirection and restoration of stdout and stderr"

    def __init__(self):
        self.real_stdout = sys.stdout
        self.real_stderr = sys.stderr
        self.fake_stdout = TextIOWrapper(BytesIO(), sys.stdout.encoding)
        self.fake_stderr = TextIOWrapper(BytesIO(), sys.stderr.encoding)
        sys.stdout = self.fake_stdout
        sys.stderr = self.fake_stderr

    # Read the content of the redirected output.
    # Returns a string tuple (stdout, stderr)
    # Can be called before or after `restore`.
    def get_output(self):
        self.fake_stdout.seek(0)
        self.fake_stderr.seek(0)

        outlines = self.fake_stdout.readlines()
        out = cull_debug_lines(outlines, self.real_stdout)

        errlines = self.fake_stderr.readlines()
        errout = cull_debug_lines(errlines, self.real_stderr)

        return out, errout

    def restore(self):
        sys.stdout = self.real_stdout
        sys.stderr = self.real_stderr

def init_testing():
    parser = OptionParser(usage="python3 -m [MODULE].test [-g]")
    parser.add_option("-g", "--debug", action="store_true", dest="debug",
                  help="debug information from failed tests")
    options, args = parser.parse_args() 
    if options.debug:
        set_debug(True)

def init_stubs(stubs=None):
    # Install stubs/mocks
    if stubs is not None:
        if type(stubs) is not list:
            stubs = [stubs]
        for stub in stubs:
            stub.use_stubs()

def check_code(mod, testName, expectedVarname, code):
    result = True
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if code != expectedValue:
            print_error("%s/%s\nExpected return code: %r\n  Actual return code: %r"
                % (mod.__name__, testName, expectedValue, code))
            result = False
    elif code != 0:
        result = False
        print_error("Unexpected nonzero return code: \"%s\"" % code)
    return result

def check_result(mod, testName, expectedVarname, testResult):
    checkResult = True
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if testResult != expectedValue:
            print_error("%s/%s\nExpected result: %r\n  Actual result: %r"
                % (mod.__name__, testName, expectedValue, testResult))
            checkResult = False
    elif not testResult:
        print_error("%s/%s: falsy result: %r" % (mod.__name__, testName, testResult))
        checkResult = False
    return checkResult

def check_output(mod, testName, expectedVarname, output, streamName):
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]

        # Replace a `TEST_DIR` directory specified in the test with the string
        # "%TEST_DIR%". When the directory is specified, do not allow matching
        # against the unmodified output, since that could cause a test to pass
        # on the machine where it was written and fail elsewhere.
        if "TEST_DIR" in mod.__dict__:
            output = output.replace(mod.__dict__["TEST_DIR"], "%TESTDIR%")

        if type(expectedValue) is Grep:
            searchVal = expectedValue.search

            # Run the check variants. If any succeed, the overall check passes.
            result = output.find(searchVal) >= 0

            if not result:
                print_error("%s/%s\nExpected: %s\n  Actual: %s"
                    % (mod.__name__, testName, searchVal, output))
        else:
            # Compare to the exact output (possibly with `TEST_DIR` replaced)
            idVariant = lambda out: out
            # Actual output will typically end with newline, but don't force
            # the test writer to specify that for everything.
            leadNlVariant = lambda out: out.removesuffix("\n")
            # Add a leading newline, to allow the test writer to use a
            # left-justified multiline string for the expected value.
            endNlVariant = lambda out: "\n" + out
            # Check with both of the newline variants above.
            sandwichNlVariant = lambda out: leadNlVariant(endNlVariant(out))

            checkVariants = [
                idVariant,
                leadNlVariant,
                endNlVariant,
                sandwichNlVariant,
            ]

            result = False
            for cv in checkVariants:
                if cv(output) == expectedValue:
                    result = True
                    break

            if not result:
                print_error("%s/%s\nExpected: %s\n  Actual: %s"
                    % (mod.__name__, testName, expectedValue, output))

    elif len(output) == 0:
        # Checks out ok: no output and no expected output
        result = True
    else:
        # Got output when none was expected
        print_error("%s/%s:\nUnexpected %s output: \"%s\""
            % (mod.__name__, testName, streamName, output))
        result = False

    return result

def run_test(mod, testName):
    '''Run a test that executes code to validate behavior

    Triggered by creating a function "test_*" in the test module.
    Intended for unit testing.
    :param mod: the test module
    :param testName: name of the test in the module (including "test_" prefix)
    :return: boolean indicating whether the test passed
    '''
    modName = mod.__name__
    fn = mod.__dict__[testName]
    type_check(fn, callable, testName)

    exception = None
    redirect_output()
    try:
        testResult = fn()
    except Exception as ex:
        exception = ex
        exceptionString = "%s: %s" % (ex.__class__.__name__, str(ex))
        print("Exception occurred during %s/%s: %s"
            % (modName, testName, exceptionString), file=sys.stderr)
        testResult = None
    out, errout = restore_output()

    result = True

    resultName = INPROCESS_RESULT_PREFIX + testName[len(INPROCESS_TEST_PREFIX):]
    if not check_result(mod, testName, resultName, testResult):
        result = False

    outName = TEST_OUTPUT_PREFIX + testName[len(INPROCESS_TEST_PREFIX):]
    if not check_output(mod, testName, outName, out, "stdout"):
        result = False

    errName = TEST_ERROR_PREFIX + testName[len(INPROCESS_TEST_PREFIX):]
    if not check_output(mod, testName, errName, errout, "stderr"):
        result = False

    if get_debug() and exception is not None:
        print_exception(exception)

    return result

def check_process_result(mod, testName, testPrefix, processResult):
    '''Validate results of a test that ran as a subprocess

    :param mod: the test module
    :param testName: name of the test in the module (including prefix)
    :param testPrefix: string prefix (e.g. "run_") of the testName
    :param processResult: result of the call to `subprocess.run`
    :return: boolean indicating whether the test passed
    '''

    code = processResult.returncode

    out = processResult.stdout
    out = out.decode('utf-8')
    out = cull_debug_text(out, sys.stdout)

    errout = processResult.stderr
    errout = errout.decode('utf-8')
    errout = cull_debug_text(errout, sys.stderr)

    testSuffix = testName[len(testPrefix):]

    result = True
    codeName = SUBPROCESS_CODE_PREFIX + testSuffix
    if not check_code(mod, testName, codeName, code):
        result = False

    outName = TEST_OUTPUT_PREFIX + testSuffix
    if not check_output(mod, testName, outName, out, "stdout"):
        result = False

    errName = TEST_ERROR_PREFIX + testSuffix
    if not check_output(mod, testName, errName, errout, "stderr"):
        result = False

    return result

def run_subprocess(mod, testName):
    '''Run a test that specifies arguments to run a subprocess

    Triggered by setting a variable "run_*" in the test module to a list of
    arguments. Intended to test user interaction and output.
    :param mod: the test module
    :param testName: name of the test in the module (including "run_" prefix)
    :return: boolean indicating whether the test passed
    '''
    args = mod.__dict__[testName]
    type_check(args, type([]), testName)

    # Pass along debug option
    if get_debug(): args.append("-g")

    dbg("Running subprocess: '%s'" % "' '".join(args))
    processResult = subprocess.run(args, capture_output=True)

    return check_process_result(
        mod,
        testName,
        SUBPROCESS_TEST_PREFIX,
        processResult)

def run_batch(mod, testName):
    '''Run a batch test that reads stdin to perform a series of operations

    Triggered by setting a variable "batch_*" in the test module to a list of
    arguments, the last of which is a string representing the newline-separated
    commands to be sent to stdin. Intended to test batch operations and output.
    :param mod: the test module
    :param testName: name of the test in the module (including "batch_" prefix)
    :return: boolean indicating whether the test passed
    '''
    values = mod.__dict__[testName]
    type_check(values, type(([],"")), testName)

    args = values[0]
    commands = values[1].encode('utf-8')

    # Pass along debug option
    if get_debug(): args.append("-g")

    dbg("Running batch process: '%s'" % "' '".join(args))

    processResult = subprocess.run(args, capture_output=True, input=commands)

    return check_process_result(
        mod,
        testName,
        BATCH_TEST_PREFIX,
        processResult)

def print_exception(exception):
    redirect_lock.acquire()
    traceback.print_exception(exception)
    redirect_lock.release()

def print_error(msg):
    redirect_lock.acquire()
    err(msg)
    redirect_lock.release()

def print_result(suiteName, modName, testName, result):
    # Producing output needs the lock to ensure redirection isn't in effect
    redirect_lock.acquire()
    if result: print_pass(suiteName, modName, testName)
    else: print_fail(suiteName, modName, testName)
    redirect_lock.release()

def print_pass(suiteName, modName, testName):
    print("%s/%s.%s: pass" % (suiteName, modName, testName))

def print_fail(suiteName, modName, testName):
    print("%s/%s.%s: FAIL" % (suiteName, modName, testName))

def wait_condition():
    return redirect is None

def redirect_output():
    global redirect, redirect_lock
    redirect_lock.acquire()
    redirect = Redirect()
 
def restore_output():
    global redirect, redirect_lock
    assert redirect is not None

    redirect.restore()
    out, errout = redirect.get_output()
    redirect = None
    redirect_lock.release()

    return out, errout

def run_test_module(mod, suiteName, results):
    '''
    Invoke all tests in a module and print individual results.

    This function is the unit of parallelism. Anything called from here should
    lock or otherwise take care before accessing shared data or resources.

    Individual tests within a module run serially to allow for intramodule data
    dependency.
    :param mod: Module, object representing the test module
    :param suiteName: string, name of the suite of which this module is part
    :param results: TestResults, an object to collect detailed test outcomes
    '''
    symNames = vars(mod)
    for symName in symNames:
        if symName.startswith(INPROCESS_TEST_PREFIX):
            result = run_test(mod, symName)
        elif symName.startswith(SUBPROCESS_TEST_PREFIX):
            result = run_subprocess(mod, symName)
        elif symName.startswith(BATCH_TEST_PREFIX):
            result = run_batch(mod, symName)
        else:
            continue

        print_result(suiteName, mod.__name__, symName, result)
        if not result: results.add_failure()
        else: results.add_success()

def run_tests(suiteName, moduleMap, copyFromToFilePairs=None):
    '''Run a set of test modules and print cumulative results.

    This function is the entry point to be called from __init__.py in the
    package directory defining a suite of test modules. Typical boilerplate is:

        from util.testing import run_tests

        def run():
            from . import mytestmodule
            from . import anothermodule

            return run_tests("suitename", locals())

    which calls this function to run the `mytestmodule` and `anothermodule` test
    modules. The grouping of modules is called "suitename" in reporting.
    :param suiteName: name of this suite of tests, for summary display purposes
    :param moduleMap: map of module names to the module object
    :param copyTmpFiles: list of tuples representing (static, dynamic) file
        paths, where static is copied to dynamic before testing, and dynamic is
        removed after testing (if debug is not enabled)
    :return: a TestResults object summarizing the results from the modules
    '''
    results = TestResults(suiteName)

    # Producing output needs the lock to ensure redirection isn't in effect
    redirect_lock.acquire()
    print("%s: running tests" % suiteName)
    redirect_lock.release()
    threads = []

    if copyFromToFilePairs is not None:
        copy_test_files(copyFromToFilePairs)

    for modName, mod in moduleMap.items():
        if MULTITHREADED:
            # Run test modules in parallel. (Individual tests within a
            # module run serially to allow for intramodule data dependency).
            t = Thread(
                name=modName,
                target=run_test_module,
                args=[mod, suiteName, results])
            threads.append(t)
            t.start()
        else:
            run_test_module(mod, suiteName, results)

    for thread in threads:
        thread.join()

    if copyFromToFilePairs is not None:
        remove_test_files(copyFromToFilePairs)

    results.print()

    return results

def copy_test_files(filePairs):
    if isinstance(filePairs, list):
        for filePair in filePairs:
            copy_test_files(filePair)
    else:
        assert isinstance(filePairs, tuple) and len(filePairs) == 2
        shutil.copy(filePairs[0], filePairs[1])

def remove_test_files(filePairs):
    if get_debug():
        return

    if isinstance(filePairs, list):
        for filePair in filePairs:
            remove_test_files(filePair)
    else:
        assert isinstance(filePairs, tuple) and len(filePairs) == 2
        os.unlink(filePairs[1])

def run_suite(suite, results):
    results.append(suite.run())

def run_test_suites(packageName, testsuites):
    '''Run a collection of testsuite modules and summarize results

    This function is the entrypoint for a test package to invoke test suites it
    contains, via the package's __init__.py file. Typical boilerplate is:

        from util.testing import run_test_suites

        def run():
            from . import unit
            from . import user
            from . import batch

            return run_test_suites("shrem", locals())

    :param packageName: descriptive name of the collection of testsuites
    :param testsuites: map or list containing modules representing testsuites;
        supports list for manual listing, and map to support passing `locals()`
    :return: TestResults object summarizing the testsuites that were run
    '''
    results = []
    threads = []
    if type(testsuites) is dict:
        testsuites = testsuites.values()
    for suite in testsuites:
        if MULTITHREADED:
            t = Thread(
                name=packageName,
                target=run_suite,
                args=[suite, results])
            threads.append(t)
            t.start()
        else:
            run_suite(suite, results)

    for thread in threads:
        thread.join()

    summary = summarize_results(packageName, *results)
    summary.print()
    return summary

def run_main_suite():
    '''Encapsulates the boilerplate needed to run a testsuite from __main__.py

    For any testsuite, the following code is all that's needed in __main__.py:

        from util.testing import run_main_suite
        from . import run
        run_main_suite()

    Note that the testsuite must import the `run` method from __init__.py.
    The process is terminated after completion.
    '''
    mainmod = sys.modules["__main__"]
    init_testing()
    sys.exit(mainmod.run().code)

