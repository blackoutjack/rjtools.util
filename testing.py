#
# Utility functions to support automated testing.
#

import sys
import os
import subprocess
from io import TextIOWrapper, BytesIO
from optparse import OptionParser

from util.msg import set_debug, dbg, info, warn, err, s_if_plural
from util.type import type_check

redirect = None

INPROCESS_TEST_PREFIX = "test_"
SUBPROCESS_TEST_PREFIX = "run_"

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

def print_result(result, modName, testName):
    print_pass(modName, testName) if result else print_fail(modName, testName)

def print_pass(modName, testName):
    print(modName + "." + testName + ": pass")

def print_fail(modName, testName):
    print(modName + "." + testName + ": fail")

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

def run_tests(modNames, modValues, suitename=None):
    testCount = 0
    failures = 0

    if suitename is not None:
        info("Running %s tests" % suitename)
    for modName in modNames:
        mod = modValues[modName]
        symNames = dir(mod)
        for symName in symNames:
            if symName.startswith(INPROCESS_TEST_PREFIX):
                testCount += 1
                result = run_test(mod, symName)
                print_result(result, modName, symName)
                if not result: failures += 1
            elif symName.startswith(SUBPROCESS_TEST_PREFIX):
                testCount += 1
                result = run_subprocess(mod, symName)
                print_result(result, modName, symName)
                if not result: failures += 1

    info("Ran %d test%s" % (testCount, s_if_plural(testCount)))
    if failures > 0:
        warn("%d failure%s" % (failures, s_if_plural(failures)))
    else:
        info("All succeeded")

    return 0 if failures == 0 else 1

