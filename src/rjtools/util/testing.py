'''Utility functions and classes to support automated testing'''

import sys
import json
import os
import re
import subprocess
import traceback
from types import ModuleType, FunctionType
from threading import Thread, RLock
from io import TextIOWrapper, BytesIO
from argparse import ArgumentParser
from queue import Queue
from pathlib import Path
from difflib import Differ
import shlex

from .msg import set_debug, get_debug, dbg, info, warn, err, s_if_plural
from .testutil import Grep, JSONFilter
from .type import type_check, empty

# Toggle parallel running of test modules. Test cases within a module are
# always run in the order they are defined in the module.
MULTITHREADED = True
# Module threads run nested within a package thread, so these numbers multiply
# to get the total max thread count.
PACKAGE_THREAD_COUNT = 2
MODULE_THREAD_COUNT = 5

# Prefixes of symbol names to use for defining test cases in a test module.
# Symbols matching these prefixes are taken up as test cases.
INPROCESS_TEST_PREFIX = "test_"
SUBPROCESS_TEST_PREFIX = "run_"
BATCH_TEST_PREFIX = "batch_"
# Add command-line arguments to the command for interactive mode.
COMMAND_PREFIX_ADDITIONS = "global_options"

# Test module symbol to specify disabled tests.
DISABLED_TESTS_SYMBOL = "DISABLED"

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
# For atomic blocks w.r.t. test module threads
module_lock = RLock()

# Easy access to ANSI color escapes
COLOR = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "GREEN": "\033[92m",
    "RED": "\033[91m",
    "YELLOW": "\033[93m",
    "ENDC": "\033[0m",
}

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

    Allow tests to run with -g without false failures due to extraneous output.
    :param lines: a string of text
    :param std: output stream to print the culled debug text
    :return: the text without debug content
    '''
    lines = text.splitlines(keepends=True)
    return cull_debug_lines(lines, std)


class Redirect(TextIOWrapper):
    """
    Manages the redirection and restoration of stdout and stderr
    """

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
    parser = ArgumentParser(usage="python3 -m [MODULE].test [-g]")
    parser.add_argument("-g", "--debug", action="store_true", dest="debug",
        help="debug information from failed tests")
    options = parser.parse_args()

    if options.debug:
        set_debug(True)


def print_expected_actual_mismatch(
        testId,
        expected,
        actual,
        expectedTitle="Expected",
        actualTitle="Actual",
        command=None):

    if empty(expected): expected = ""
    if empty(actual): actual = ""

    d = Differ()
    diff = d.compare(expected.splitlines(), actual.splitlines())

    header = "%s%s%s%s%s" % (
        "%s\n" % testId,
        '' if empty(command) is None else "%s\n" % (command),
        '' if empty(expected) else "--- <%s%s%s>" % (COLOR["RED"], expectedTitle, COLOR["HEADER"]),
        '' if empty(expected) or empty(actual) else ', ',
        '' if empty(actual) else "+++ <%s%s%s>" % (COLOR["GREEN"], actualTitle, COLOR["HEADER"])
    )

    lines = [COLOR["HEADER"] + header + COLOR["ENDC"]]
    for line in diff:
        if line.startswith('+'):
            lines.append(COLOR["GREEN"] + line + COLOR["ENDC"])
        elif line.startswith('-'):
            lines.append(COLOR["RED"] + line + COLOR["ENDC"])
        elif line.startswith('?'):
            lines.append(COLOR["YELLOW"] + line + COLOR["ENDC"])
        else:
            lines.append(line)
    diffText = "\n".join(lines)

    print_divider()

    print_error("%s" % diffText)


def check_code(mod, testName, expectedVarname, code, command=None):
    result = True
    testId = get_test_identifier(mod, testName)
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if code != expectedValue:
            print_divider()
            print_expected_actual_mismatch(
                testId,
                "%r" % expectedValue,
                "%r" % code,
                expectedTitle="Expected return code",
                actualTitle="Actual return code",
                command=command)
            result = False
    elif code != 0:
        print_divider()
        # Got output when none was expected
        print_expected_actual_mismatch(
            testId,
            None,
            str(code),
            actualTitle="Unexpected nonzero return code",
            command=command)
        result = False
    return result


def check_result(mod, testName, expectedVarname, testResult, command=None):
    checkResult = True
    testId = get_test_identifier(mod, testName)
    if expectedVarname in mod.__dict__:
        expectedValue = mod.__dict__[expectedVarname]
        if testResult != expectedValue:
            print_divider()
            print_expected_actual_mismatch(
                testId,
                "%r" % expectedValue,
                "%r" % testResult,
                expectedTitle="Expected result",
                actualTitle="Actual result",
                command=command)
            checkResult = False
    elif not testResult:
        print_divider()
        print_expected_actual_mismatch(
            testId,
            None,
            "%r" % testResult,
            actualTitle="False result",
            command=command)
        print_error("%s: falsy result: %r" % (testId, testResult))
        checkResult = False
    return checkResult


def get_test_identifier(mod, testName):
    return "%s/%s" % (mod.__name__, testName)


def check_output(mod, testName, expectedVarname, output, streamName, command=None):
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
            result = re.search(searchVal, output)
            #result = output.find(searchVal) >= 0

            # %%% Provide the test a way to retrieve regex matches.

            result = False if result is None else True

            if not result:
                print_expected_actual_mismatch(
                    testId,
                    searchVal,
                    output,
                    expectedTitle="Expected %s substring" % streamName,
                    actualTitle="Actual %s output" % streamName,
                    command=command)

        else:
            if type(expectedValue) is JSONFilter:
                try:
                    # Remove the specified attributes from the JSON output
                    output = expectedValue.applyFilter(output)
                    expectedValue = expectedValue.text
                except json.JSONDecodeError as ex:
                    err("Invalid JSON supplied in test %s: %s" % (testName, str(ex)))
                    return False

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
                    expectedTitle="Expected %s output" % streamName,
                    actualTitle="Actual %s output" % streamName,
                    command=command)

    elif len(output) == 0:
        # Checks out ok: no output and no expected output
        result = True
    else:
        # Got output when none was expected
        print_expected_actual_mismatch(
            testId,
            None,
            output,
            actualTitle="Unexpected %s output" % streamName,
            command=command)
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

    # Matched to release() after print_result in caller.
    module_lock.acquire()

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


def check_process_result(mod, testName, testPrefix, processResult, command=None):
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
    if not check_code(mod, testName, codeName, code, command):
        result = False

    outName = TEST_OUTPUT_PREFIX + testSuffix
    if not check_output(mod, testName, outName, out, "stdout", command):
        result = False

    errName = TEST_ERROR_PREFIX + testSuffix
    if not check_output(mod, testName, errName, errout, "stderr", command):
        result = False

    return result


def run_subprocess(mod, testName, commandPrefix=None):
    '''Run a test that specifies arguments to run a subprocess

    Triggered by setting a variable "run_*" in the test module to a list of
    arguments. Intended to test user interaction and output.
    :param mod: the test module
    :param testName: name of the test in the module (including "run_" prefix)
    :return: boolean indicating whether the test passed
    '''
    args = mod.__dict__[testName]
    type_check(args, type([]), testName)

    if commandPrefix is not None:
        type_check(commandPrefix, type([]), testName)
        args = commandPrefix + args

    # Pass along debug option
    if get_debug(): args.append("-g")

    try:
        commandText = shlex.join(args)
    except TypeError as ex:
        # Matched to release() after print_result in caller.
        module_lock.acquire()
        print_divider()
        print_error("%sCommand arguments contain unsupported types: %r%s" % (COLOR["RED"], args, COLOR["ENDC"]))
        return False

    dbg("Running subprocess: %s" % commandText)
    processResult = subprocess.run(args, capture_output=True, env=os.environ)

    # Matched to release() after print_result in caller.
    module_lock.acquire()

    return check_process_result(
        mod,
        testName,
        SUBPROCESS_TEST_PREFIX,
        processResult,
        commandText)


def run_batch(mod, testName, commandPrefix=None):
    '''Run a batch test that reads stdin to perform a series of operations

    Triggered by setting a variable "batch_*" in the test module to a list of
    arguments, the last of which is a string representing the newline-separated
    commands to be sent to stdin. Intended to test batch operations and output.
    :param mod: the test module
    :param testName: name of the test in the module (including "batch_" prefix)
    :return: boolean indicating whether the test passed
    '''
    values = mod.__dict__[testName]
    if type(values) is str:
        # Specifying command arguments are optional, as long as there is
        # something in commandPrefix.
        type_check(commandPrefix, type([]), testName)
        if len(commandPrefix) == 0:
            err("Cannot run a batch command in test %s with no arguments" % testName)
            return False
        args = commandPrefix
        commands = values
    else:
        type_check(values, type(([],"")), testName)

        args = values[0]
        if commandPrefix is not None:
            type_check(commandPrefix, type([]), testName)
            args = commandPrefix + args

        commands = values[1]

    commands = commands.encode('utf-8')

    # Pass along debug option
    if get_debug(): args.append("-g")

    dbg("Running batch process: '%s'" % "' '".join(args))

    processResult = subprocess.run(args, capture_output=True, input=commands, env=os.environ)

    # Matched to release() after print_result in caller.
    module_lock.acquire()

    return check_process_result(
        mod,
        testName,
        BATCH_TEST_PREFIX,
        processResult)


def print_exception(exception):
    redirect_lock.acquire()
    traceback.print_exception(exception)
    redirect_lock.release()


def print_divider():
    redirect_lock.acquire()
    info("===================================")
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
    print_divider()


def copy_store_to_mirror(sourceOption, targetOption):
    venvActivate = os.path.join(Path.home(), ".venvs", "shrem", "bin", "activate")
    shremDir = os.path.join(Path.home(), "lib", "shrem")

    # %%% Hack to avoid breaking prod during development
    convertArg = "convert" if "NEWCONVERT" in os.environ else "--convert"
    # %%% Requires running with virtualenv already activated.
    args = ["python", "-m", "shrem", convertArg, "--store", sourceOption, "--target", targetOption]

    dbg("Running subprocess: '%s'" % "' '".join(args))
    processResult = subprocess.run(args)
    code = processResult.returncode
    if code != 0:
        err("Failed to copy store %s to mirror %s" % (sourceOption, targetOption))


def initialize_dynamic_test_stores(testPackages):
    '''Copy source files/databases to associated mirrors for testing'''
    if not type(testPackages) is list:
        testPackages = [testPackages]

    storeMap = {}
    for testPackage in testPackages:
        packageDict = testPackage.__dict__
        if "TEST_STORE_OPTION" not in packageDict:
            continue

        testStoreOption = packageDict["TEST_STORE_OPTION"]
        # Causes error if not defined.
        mirrorStoreOption = packageDict["MIRROR_STORE_OPTION"]

        # May happen if two packages submit the same static file.
        if testStoreOption in storeMap:
            assert storeMap[testStoreOption] == mirrorStoreOption
            continue

        storeMap[testStoreOption] = mirrorStoreOption

    for testStoreOption, mirrorStoreOption in storeMap.items():
        copy_store_to_mirror(testStoreOption, mirrorStoreOption)


def clean_dynamic_test_stores(dynamicTestStores):
    '''Remove dynamically-created test files'''
    dbg("IN CLEAN DYNAMIC TEST STORES: %r" % dynamicTestStores)
    if not get_debug():
        for testStore in dynamicTestStores:
            os.unlink(testStore)
    if "TESTING_URL_MIRROR_MAP" in os.environ:
        del os.environ["TESTING_URL_MIRROR_MAP"]


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


def run_module(mod:ModuleType, packageName, results, commandPrefix=None):
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
    dbg("Running module: %r" % mod.__name__)
    disabled = getattr(mod, DISABLED_TESTS_SYMBOL, [])
    if not isinstance(disabled, list):
        dbg("Unexpected type for special symbol %s, ignoring" % DISABLED_TESTS_SYMBOL)
        disabled = []

    extendedCommandPrefix = None if commandPrefix is None else commandPrefix.copy()

    symNames = vars(mod)
    for symName in symNames:
        if symName in disabled:
            dbg("Skipping disabled test: %s" % symName)
            continue
        if symName == COMMAND_PREFIX_ADDITIONS:
            extendedCommandPrefix.extend(mod.__dict__[symName])
            continue
        elif symName.startswith(INPROCESS_TEST_PREFIX):
            result = run_test(mod, symName)
        elif symName.startswith(SUBPROCESS_TEST_PREFIX):
            result = run_subprocess(mod, symName, extendedCommandPrefix)
        elif symName.startswith(BATCH_TEST_PREFIX):
            result = run_batch(mod, symName, extendedCommandPrefix)
        else:
            continue

        print_result(packageName, mod.__name__, symName, result)
        module_lock.release()
        if not result: results.add_failure()
        else: results.add_success()


def run_modules(packageName, moduleMap, commandPrefix=None):
    '''Run a set of test modules and print cumulative results.

    This function is the entry point to be called from __init__.py in the
    package directory defining a suite of test modules. Typical boilerplate is:

        from rjtools.util.testing import run_modules

        def run():
            from . import mytestmodule
            from . import anothermodule

            return run_modules("package name", locals())

    which calls this function to run the `mytestmodule` and `anothermodule` test
    modules. The grouping of modules is called "suitename" in reporting.
    :param packageName: name of the test package, for summary display purposes
    :param moduleMap: map of module name to the module object
    :param commandPrefix: list of command-line arguments to prepend
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
                run_module(mod, pkgName, res, commandPrefix)
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
            run_module(testModule, packageName, results, commandPrefix)

    results.print()

    return results


def run_package(package, results):
    try:
        dbg("Running package %s" % package.__name__)
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

        from rjtools.util.testing import run_packages

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
    dbg("Initializing suite %s" % suiteName)
    results = []
    threads = []

    initialize_dynamic_test_stores(list(packageMap.values()))

    if MULTITHREADED:
        q = Queue()

        def worker(res):
            while True:
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

        from rjtools.util.testing import run_suite
        from . import run
        run_suite()

    Note that the test suite must import the `run` method from __init__.py.
    The process is terminated after completion.
    '''
    mainmod = sys.modules["__main__"]

    initialize_dynamic_test_stores(mainmod)
    if not isinstance(mainmod.run, FunctionType):
        raise ValueError(f"No 'run' function found in module {mainmod.__name__}")

    init_testing()
    result = mainmod.run()

    sys.exit(result.code)
