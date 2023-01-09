
import sys
import os
from io import TextIOWrapper, BytesIO
from optparse import OptionParser

from util.msg import set_debug, dbg, info, warn, err, s_if_plural
from util.type import type_check

redirect = None

# Manages the redirection and restoration of stdout and stderr
class Redirect(TextIOWrapper):

    def __init__(self):
        self.real_stdout = sys.stdout
        self.real_stderr = sys.stderr
        self.fake_stdout = TextIOWrapper(BytesIO(), sys.stdout.encoding)
        self.fake_stderr = TextIOWrapper(BytesIO(), sys.stderr.encoding)
        sys.stdout = self.fake_stdout
        sys.stderr = self.fake_stderr

    # Remove lines formatted like debug output. Allows running tests with -g
    # without creating false failures due to extraneous output.
    def cull_debug(self, lines, std):
        out = ""
        for line in lines:
            if line.startswith("DEBUG: "):
                print(line, file=std, end='')
            else:
                out += line
        return out

    # Read the content of the redirected output.
    # Returns a string tuple (stdout, stderr)
    # Can be called before or after `restore`.
    def get_output(self):
        self.fake_stdout.seek(0)
        self.fake_stderr.seek(0)

        outlines = self.fake_stdout.readlines()
        out = self.cull_debug(outlines, self.real_stdout)

        errlines = self.fake_stderr.readlines()
        errout = self.cull_debug(errlines, self.real_stderr)

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

def check_output(mod, expectedVarname, output, streamName):
    result = True
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if output != expectedValue:
            # Actual output will typically have a newline, but don't force the
            # test creator to specify that for everything.
            if output.endswith("\n"):
                output = output[:-1]
            moddir = os.path.dirname(mod.__file__)
            output = output.replace(moddir, "%TESTDIR%")
            if output != expectedValue:
                err("\nExpected: %r\n  Actual: %r" % (expectedValue, output))
                result = False
    elif len(output) > 0:
        result = False
        err("Unexpected %s output: \"%s\"" % (streamName, output))
    return result

def run_test(mod, testName):
    fn = mod.__dict__[testName]
    def checkfn(): pass
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

    outName = "out_" + testName[5:]
    if not check_output(mod, outName, out, "stdout"): result = False
    errName = "err_" + testName[5:]
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

def run_tests(modNames, modValues):
    testCount = 0
    failures = 0

    for modName in modNames:
        mod = modValues[modName]
        symNames = dir(mod)
        for symName in symNames:
            if symName.startswith("test_"):
                testCount += 1
                result = run_test(mod, symName)
                print_result(result, modName, symName)
                if not result: failures += 1

    info("Ran %d test%s" % (testCount, s_if_plural(testCount)))
    if failures > 0:
        warn("%d failure%s" % (failures, s_if_plural(failures)))
    else:
        info("No failures")

    return 0 if failures == 0 else 1

