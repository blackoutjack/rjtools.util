'''Test behaviors of the util.logging module

'''

from util.log import Logger

logger = Logger()

def test_log_info():
    logger.info("testing output to stdout")
    return True

out_log_info = "INFO: testing output to stdout"

def test_log_warn():
    logger.warn("warning to stdout")
    return True

err_log_warn = "WARNING: warning to stdout"

def test_log_err():
    logger.err("error to stdout")
    return True

err_log_err = "ERROR: error to stdout"

