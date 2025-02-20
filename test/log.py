'''Test behaviors of the util.logging module

'''

from dgutil.log import Logger

defaultLogger = Logger()

def test_log_info():
    defaultLogger.info("testing output to stdout")
    return True

out_log_info = "testing output to stdout"

def test_log_warn():
    defaultLogger.warn("warning to stdout")
    return True

err_log_warn = "WARNING: warning to stdout"

def test_log_err():
    defaultLogger.err("error to stdout")
    return True

err_log_err = "ERROR: error to stdout"

