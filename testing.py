'''Utility functions and classes to support automated testing'''

import sys
import json
import os
import random
import shutil
import subprocess
import tempfile
import traceback
from types import ModuleType
import threading
from threading import Thread, Condition, RLock
from io import TextIOWrapper, BytesIO
from optparse import OptionParser
from queue import Queue

from util.msg import set_debug, get_debug, dbg, info, warn, err, s_if_plural
from util.testutil import Grep
from util.type import type_check

# Toggle parallel running of test modules. Test cases within a module are
# always run in the order they are defined in the module.
MULTITHREADED = True
# Module threads run nested within a package thread, so these numbers multiply
# to get the total max thread count.
PACKAGE_THREAD_COUNT = 4
MODULE_THREAD_COUNT = 4

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

# This string, unique to the top-level testing script, can be
# used to, e.g., make a writable copy of a static file that will be
# modified in the course of testing.
TESTING_TOKEN = "_test%d" % os.getpid()

# Thread
redirect = None
# Thread lock for coordinating
redirect_lock = RLock()
# Lock when updating environment variables
environ_lock = RLock()

class TestResults:
    def __init__(self, packageName):
        self.name = packageName
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

def summarize_results(name, *results):
    '''Produce a summary TestResults object from the given results

    :param name: a descriptive name for the summary results
    :param results: TestResults objects to be summarized
    :return: a summary TestResults object
    '''
    summary = TestResults(name)
    if len(results) == 0:
        summary.total = 0
        summary.failures = 0
        summary.code = 0
    else:
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

def print_expected_actual_mismatch(
        testId,
        expected,
        actual,
        expectedPrompt="Expected:",
        actualPrompt="Actual:"):
    expectedHasNewline = expected is not None and expected.find("\n") > -1
    actualHasNewline = actual is not None and actual.find("\n") > -1
    if expectedHasNewline or actualHasNewline:
        # When values that contain newlines are involved, it looks better and
        # makes it easier to compare to ensure both values have an initial
        # newline.
        if expected is not None and len(expected) > 0 and expected[0] != "\n":
            expected = "\n%s" % expected
        if actual is not None and len(actual) > 0 and actual[0] != "\n":
            actual = "\n%s" % actual
    else:
        # Add a space for looks
        if expected is not None and actual is not None:
            alignRight = max(len(expectedPrompt), len(actualPrompt))
            while len(expectedPrompt) < alignRight:
                expectedPrompt = " %s" % expectedPrompt
            while len(actualPrompt) < alignRight:
                actualPrompt = " %s" % actualPrompt
        expectedPrompt = "%s " % expectedPrompt
        actualPrompt = "%s " % actualPrompt

    expectedDisplay = '' if expected is None else "%s%s" % (
        expectedPrompt, expected)
    actualDisplay = '' if actual is None else "%s%s" % (actualPrompt, actual)

    print_error("%s\n%s\n%s"
        % (testId, expectedDisplay, actualDisplay))

def check_code(mod, testName, expectedVarname, code):
    result = True
    testId = get_test_identifier(mod, testName)
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if code != expectedValue:
            print_expected_actual_mismatch(
                testId,
                "%r" % expectedValue,
                "%r" % code,
                expectedPrompt="Expected return code:",
                actualPrompt="Actual return code:")
            result = False
    elif code != 0:
        result = False
        # Got output when none was expected
        print_expected_actual_mismatch(
            testId,
            None,
            str(code),
            actualPrompt="Unexpected nonzero return code:")
    return result

def check_result(mod, testName, expectedVarname, testResult):
    checkResult = True
    testId = get_test_identifier(mod, testName)
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if testResult != expectedValue:
            print_expected_actual_mismatch(
                testId,
                "%r" % expectedValue,
                "%r" % testResult,
                expectedPrompt="Expected result:",
                actualPrompt="Actual result:")
            checkResult = False
    elif not testResult:
        print_expected_actual_mismatch(
            testId,
            None,
            "%r" % testResult,
            actualPrompt="False result:")
        print_error("%s: falsy result: %r" % (testId, testResult))
        checkResult = False
    return checkResult

def get_test_identifier(mod, testName):
    return "%s/%s" % (mod.__name__, testName)

def check_output(mod, testName, expectedVarname, output, streamName):
    testId = get_test_identifier(mod, testName)
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
                print_expected_actual_mismatch(
                    testId,
                    searchVal,
                    output,
                    expectedPrompt="Expected %s substring:" % streamName,
                    actualPrompt="Actual %s output:" % streamName)
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
                print_expected_actual_mismatch(
                    testId,
                    expectedValue,
                    output,
                    expectedPrompt="Expected %s output:" % streamName,
                    actualPrompt="Actual %s output:" % streamName)

    elif len(output) == 0:
        # Checks out ok: no output and no expected output
        result = True
    else:
        # Got output when none was expected
        print_expected_actual_mismatch(
            testId,
            None,
            output,
            actualPrompt="Unexpected %s output:" % streamName)
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
    processResult = subprocess.run(args, capture_output=True, env=os.environ)

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

    processResult = subprocess.run(args, capture_output=True, input=commands, env=os.environ)

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

def print_result(packageName, modName, testName, result):
    # Producing output needs the lock to ensure redirection isn't in effect
    redirect_lock.acquire()
    if result: print_pass(packageName, modName, testName)
    else: print_fail(packageName, modName, testName)
    redirect_lock.release()

def print_pass(packageName, modName, testName):
    print("%s/%s.%s: pass" % (packageName, modName, testName))

def print_fail(packageName, modName, testName):
    print("%s/%s.%s: FAIL" % (packageName, modName, testName))

def add_paths_to_set(module, pathOrPaths, theList):
    dbg("PATH: %r, MODULEPATH: %r" % (pathOrPaths, module.__file__))
    if isinstance(pathOrPaths, str):
        path = pathOrPaths
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(module.__file__), path)
        theList.add(os.path.abspath(path))
    elif isinstance(pathOrPaths, list):
        for path in pathOrPaths:
            add_paths_to_set(module, path, theList)
    else:
        raise ValueError("Unexpected value type for paths: %r"
            % type(pathOrPaths))

def load_static_test_files_from_package(package, uniqueFiles):
    if "test_files" in vars(package):
        filesToCopy = package.__dict__["test_files"]
        dbg("FILESTOCOPY: %r" % filesToCopy)
        add_paths_to_set(package, filesToCopy, uniqueFiles)

def load_static_test_files(testPackages):
    uniqueFiles = set()
    if isinstance(testPackages, list):
        for package in testPackages:
            load_static_test_files_from_package(package, uniqueFiles)
    elif isinstance(testPackages, ModuleType):
        load_static_test_files_from_package(testPackages, uniqueFiles)
    else:
        raise ValueError("Unexpected value type for test package: %r"
            % type(testPackages))

    dbg("UNIQUEFILES: %r" % uniqueFiles)
    return uniqueFiles

def initialize_dynamic_test_files(staticTestFiles):
    '''Copy files and set envvar to communicate path

    :return: list of string file paths of dynamic test files
    '''
    environ_lock.acquire()
    staticDynamicMap = json.loads(os.environ.get("TESTING_FILES", "{}"))
    dbg("EXISTING STATICDYNAMICMAP: %r" % staticDynamicMap)
    for staticFile in staticTestFiles:
        base, ext = os.path.splitext(staticFile)
        dynamicFile = "%s%s%s" % (base, TESTING_TOKEN, ext)
        dynamicFile = os.path.join(
            tempfile.gettempdir(),
            "util.testing",
            os.path.relpath(dynamicFile, '/'))

        # May happen if two packages submit the same static file.
        if staticFile in staticDynamicMap:
            assert staticDynamicMap[staticFile] == dynamicFile
            continue

        os.makedirs(os.path.dirname(dynamicFile), exist_ok=True)
        dbg("COPYING: %s => %s" % (staticFile, dynamicFile))
        shutil.copy(staticFile, dynamicFile)
        staticDynamicMap[staticFile] = dynamicFile

    # This will guide in-process testing and will be propagated to subprocesses.
    os.environ["TESTING_FILES"] = json.dumps(staticDynamicMap)
    environ_lock.release()
    return staticDynamicMap.values()

def clean_dynamic_test_files(dynamicTestFiles):
    '''Remove dynamically-created test files'''
    dbg("IN CLEAN DYNAMIC TEST FILES: %r" % dynamicTestFiles)
    if not get_debug():
        for testFile in dynamicTestFiles:
            os.unlink(testFile)
    if "TESTING_FILES" in os.environ:
        del os.environ["TESTING_FILES"]

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

def run_module(mod, packageName, results):
    '''
    Invoke all tests in a module and print individual results.

    This function is the unit of parallelism. Anything called from here should
    lock or otherwise take care before accessing shared data or resources.

    Individual tests within a module run serially to allow for intramodule data
    dependency.
    :param mod: Module, object representing the test module
    :param packageName: string, name of the package of which this module is part
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

        print_result(packageName, mod.__name__, symName, result)
        if not result: results.add_failure()
        else: results.add_success()

def run_modules(packageName, moduleMap):
    '''Run a set of test modules and print cumulative results.

    This function is the entry point to be called from __init__.py in the
    package directory defining a suite of test modules. Typical boilerplate is:

        from util.testing import run_modules

        def run():
            from . import mytestmodule
            from . import anothermodule

            return run_modules("package name", locals())

    which calls this function to run the `mytestmodule` and `anothermodule` test
    modules. The grouping of modules is called "suitename" in reporting.
    :param packageName: name of the test package, for summary display purposes
    :param moduleMap: map of module name to the module object
    :return: a TestResults object summarizing the results from the modules
    '''
    results = TestResults(packageName)

    # Producing output needs the lock to ensure redirection isn't in effect
    redirect_lock.acquire()
    print("%s: running tests" % packageName)
    redirect_lock.release()

    if MULTITHREADED:

        q = Queue()

        def worker(pkgName, res):
            while True:
                mod = q.get()
                run_module(mod, pkgName, res)
                q.task_done()

        for threadNum in range(MODULE_THREAD_COUNT):
            # Run test modules in parallel. (Individual tests within a
            # module run serially to allow for intramodule data dependency).
            t = Thread(
                name="run_module%d" % threadNum,
                target=worker,
                args=[packageName, results])
            t.daemon = True
            t.start()

        for testModule in moduleMap.values():
            q.put(testModule)

        q.join()

    else:
        for testModule in moduleMap.values():
            run_module(testModule, packageName, results)

    results.print()

    return results

def run_package(package, results):
    try:
        result = package.run()
    except Exception as ex:
        # Catch any problems that occur while loading the top-level code of a
        # test module.
        result = TestResults("")
        result.add_failure()
        print_error("Exception occurred while loading modules in package %s: %s" % (package.__name__, str(ex)))
        print_exception(ex)

    results.append(result)


def run_packages(suiteName, packageMap):
    '''Run a collection of test packages typically corresponding to an app.

    The packages correspond to Python packages, and are comprised of test
    modules corresponding to Python modules.

    This function is the entrypoint for a test suite to invoke test packages
        it contains, via the package's __init__.py file. Typical boilerplate is:

        from util.testing import run_packages

        def run():
            from . import unit
            from . import user
            from . import batch

            return run_packages("suite name", locals())

    :param suiteName: descriptive name of test suite containing these packages
    :param packageMap: map containing package objects (of type
        ModuleType) representing test packages; supports list for manual
        listing, and map to support passing `locals()`
    :return: TestResults object summarizing the test packages that were run
    '''
    results = []
    threads = []

    staticTestFiles = load_static_test_files(list(packageMap.values()))
    dynamicTestFiles = initialize_dynamic_test_files(staticTestFiles)

    if MULTITHREADED:
        q = Queue()

        def worker(res):
            pkg = q.get()
            run_package(pkg, res)
            q.task_done()

        for threadNum in range(PACKAGE_THREAD_COUNT):
            t = Thread(
                name="run_package%d" % threadNum,
                target=worker,
                args=[results])
            t.daemon = True
            t.start()

        for package in packageMap.values():
            q.put(package)

        q.join()

    else:
        for packageName, package in packageMap.items():
            run_package(package, results)

    summary = summarize_results(suiteName, *results)
    summary.print()
    return summary

def run_suite():
    '''Encapsulates the boilerplate needed to run a test suite from __main__.py

    For any test suite/package, the following code is all that's needed in
    __main__.py:

        from util.testing import run_suite
        from . import run
        run_suite()

    Note that the test suite must import the `run` method from __init__.py.
    The process is terminated after completion.
    '''
    mainmod = sys.modules["__main__"]

    staticTestFiles = load_static_test_files(mainmod)
    dynamicTestFiles = initialize_dynamic_test_files(staticTestFiles)

    init_testing()
    result = mainmod.run()

    clean_dynamic_test_files(dynamicTestFiles)

    sys.exit(result.code)

