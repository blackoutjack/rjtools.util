#
# Utility functions for generating standardized text output.
#

import sys

DEBUG = False

MESSAGE_LOG = []
INFO_LOG = []

LOG_INFO_OUTPUT = True

STANDARD_OUTPUT = True

ERROR_LOG = None

def set_debug(val):
    global DEBUG
    DEBUG = val

def get_debug():
    return DEBUG

def get_message_log():
    global MESSAGE_LOG, LOG_INFO_OUTPUT
    if LOG_INFO_OUTPUT: MESSAGE_LOG.append({ "type": "info", "message": "\n".join(INFO_LOG) })
    return MESSAGE_LOG

def disable_standard_output():
    global STANDARD_OUTPUT
    STANDARD_OUTPUT = False

def disable_info_logging():
    global LOG_INFO_OUTPUT
    LOG_INFO_OUTPUT = False

def enable_standard_output():
    global STANDARD_OUTPUT
    STANDARD_OUTPUT = True

def dbg(msg, target=None):
    if DEBUG:
        if target is None: target = sys.stdout
        if type(msg) is str:
            msgText = msg
        else:
            msgText = "%r" % msg

        if STANDARD_OUTPUT:
            print("DEBUG: %s" % msgText, file=target)
        MESSAGE_LOG.append({ "type": "debug", "message": msgText })

def info(msg, indent="", target=None):
    if target is None: target = sys.stdout
    if STANDARD_OUTPUT:
        print("%s%s" % (indent, msg), file=target)
    if LOG_INFO_OUTPUT:
        INFO_LOG.append(msg)
        #MESSAGE_LOG.append({ "type": "info", "message": msg })

def warn(msg, indent="", target=None):
    if target is None: target = sys.stderr
    if STANDARD_OUTPUT:
        print("%sWARNING: %s" % (indent, msg), file=target)
    MESSAGE_LOG.append({ "type": "warn", "message": msg })

def err(msg, indent="", target=None):
    if target is None: target = sys.stderr
    if STANDARD_OUTPUT:
        print("%sERROR: %s" % (indent, msg), file=target)
    MESSAGE_LOG.append({ "type": "error", "message": msg })

def s_if_plural(count):
    return "" if count == 1 else "s"

# %%% Handle cases where num > 26 (return "AA", "AB" and so forth)
def alpha(num, lower=False):
    shift = 96 if lower else 64
    return chr(num + shift)

# %%% Handle double/triple/etc letters ("AA"=27, "AB"=28 and so forth)
def num(alpha):
    lower = alpha.lower() == alpha
    shift = 96 if lower else 64
    return ord(alpha) - shift
