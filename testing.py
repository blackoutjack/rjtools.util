#
# Utility functions and classes to support automated testing.
#

import sys
import os
import subprocess
from io import TextIOWrapper, BytesIO
from optparse import OptionParser

from util.msg import set_debug, get_debug, dbg, info, warn, err, s_if_plural
from util.type import type_check

redirect = None

INPROCESS_TEST_PREFIX = "test_"
SUBPROCESS_TEST_PREFIX = "run_"

class TestResults:
    def __init__(self, suitename):
        self.name = suitename
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

def check_code(mod, expectedVarname, code):
    result = True
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if code != expectedValue:
            err("%s\nExpected return code: %r\n  Actual return code: %r"
                % (mod.__name__, expectedValue, code))
            result = False
    elif code != 0:
        result = False
        err("Unexpected nonzero return code: \"%s\"" % code)
    return result

def check_output(mod, expectedVarname, output, streamName):
    result = True
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if output != expectedValue:
            # Actual output will typically have a newline, but don't force the
            # test creator to specify that for everything.
            if output.endswith("\n"):
                output = output[:-1]
            # Substitute a token for a directory as specified by the test.
            if "TEST_DIR" in mod.__dict__:
                testdir = mod.__dict__["TEST_DIR"]
                output = output.replace(testdir, "%TESTDIR%")
            if output != expectedValue:
                err("%s\nExpected: %r\n  Actual: %r"
                    % (mod.__name__, expectedValue, output))
                result = False
    elif len(output) > 0:
        result = False
        err("Unexpected %s output: \"%s\"" % (streamName, output))
    return result

def run_test(mod, testName):
    '''Run a test that executes code to validate behavior

    Triggered by creating a function "test_*" in the test module.
    Intended for unit testing.
    :param mod: the test module
    :param testName: the name of the test in the module
    :return: boolean indicating whether the test passed
    '''
    fn = mod.__dict__[testName]
    type_check(fn, callable, testName)

    redirect_output()
    try:
        result = fn()
    except Exception as ex:
        print(str(ex))
        result = False
    out, errout = restore_output()

    if not result:
        err("Falsy result for %s: %r" % (testName, result))

    outName = "out_" + testName[len(INPROCESS_TEST_PREFIX):]
    if not check_output(mod, outName, out, "stdout"): result = False
    errName = "err_" + testName[len(INPROCESS_TEST_PREFIX):]
    if not check_output(mod, errName, errout, "stderr"): result = False

    return result

# %%% Parallelize
def run_subprocess(mod, testName):
    '''Run a test that specifies arguments to run a subprocess

    Triggered by setting a variable "run_*" in the test module to a list of
    arguments. Intended to test user interaction and output.
    :param mod: the test module
    :param testName: the name of the test in the module
    :return: boolean indicating whether the test passed
    '''
    args = mod.__dict__[testName]
    type_check(args, type([]), testName)

    # Pass along debug option
    if get_debug(): args.append("-g")

    dbg("Running subprocess: '%s'" % "' '".join(args))
    processresult = subprocess.run(args, capture_output=True)
    code = processresult.returncode

    out = processresult.stdout
    out = out.decode('utf-8')
    out = cull_debug_text(out, sys.stdout)

    errout = processresult.stderr
    errout = errout.decode('utf-8')
    errout = cull_debug_text(errout, sys.stderr)

    result = True
    codeName = "code_" + testName[len(SUBPROCESS_TEST_PREFIX):]
    if not check_code(mod, codeName, code): result = False
    outName = "out_" + testName[len(SUBPROCESS_TEST_PREFIX):]
    if not check_output(mod, outName, out, "stdout"): result = False
    errName = "err_" + testName[len(SUBPROCESS_TEST_PREFIX):]
    if not check_output(mod, errName, errout, "stderr"): result = False

    return result

def print_result(suitename, modName, testName, result):
    if result: print_pass(suitename, modName, testName)
    else: print_fail(suitename, modName, testName)

def print_pass(suitename, modName, testName):
    print("%s/%s.%s: pass" % (suitename, modName, testName))

def print_fail(suitename, modName, testName):
    print("%s/%s.%s: FAIL" % (suitename, modName, testName))

def redirect_output():
    global redirect
    if redirect is None:
        redirect = Redirect()
 
def restore_output():
    global redirect
    if redirect is not None:
        redirect.restore()
        out, errout = redirect.get_output()
        redirect = None

        return out, errout

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

def run_test_suites(name, *testsuites):
    '''Run a collection of testsuite modules and summarize results

    :param name: descriptive name of the collection of testsuites
    :param testsuites: list of modules representing the testsuites to be run
    :return: TestResults object summarizing the testsuites that were run
    '''
    results = []
    for suite in testsuites:
        results.append(suite.run())

    summary = summarize_results(name, *results)
    summary.print()
    return summary

def run_tests(modNames, modValues, suitename):
    results = TestResults(suitename)

    print("%s: running tests" % suitename)
    for modName in modNames:
        mod = modValues[modName]
        symNames = dir(mod)
        for symName in symNames:
            if symName.startswith(INPROCESS_TEST_PREFIX):
                result = run_test(mod, symName)
                print_result(suitename, modName, symName, result)
                if not result: results.add_failure()
                else: results.add_success()
            elif symName.startswith(SUBPROCESS_TEST_PREFIX):
                result = run_subprocess(mod, symName)
                print_result(suitename, modName, symName, result)
                if not result: results.add_failure()
                else: results.add_success()

    results.print()

    return results

