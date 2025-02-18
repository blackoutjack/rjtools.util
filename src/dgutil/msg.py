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

def clear_message_log():
    global MESSAGE_LOG, INFO_LOG
    MESSAGE_LOG = []
    INFO_LOG = []

def get_message_log():
    global MESSAGE_LOG, LOG_INFO_OUTPUT
    if LOG_INFO_OUTPUT and len(INFO_LOG) > 0:
        MESSAGE_LOG.append({ "type": "info", "message": "\n".join(INFO_LOG) })
    return MESSAGE_LOG

def filter_messages():
    global STANDARD_OUTPUT
    STANDARD_OUTPUT = False

def disable_info_logging():
    global LOG_INFO_OUTPUT
    LOG_INFO_OUTPUT = False

def unfilter_messages():
    global STANDARD_OUTPUT
    STANDARD_OUTPUT = True

def dbg(msg, target=None):
    if DEBUG:
        if target is None: target = sys.stdout
        if type(msg) is str:
            msgText = msg
        else:
            msgText = str(msg)

        if STANDARD_OUTPUT:
            print("DEBUG: %s" % msgText, file=target)
        MESSAGE_LOG.append({ "type": "debug", "message": msgText })

def info(msg, indent="", target=None):
    if target is None: target = sys.stdout
    if STANDARD_OUTPUT:
        print("%s%s" % (indent, str(msg)), file=target)
    if LOG_INFO_OUTPUT:
        INFO_LOG.append(str(msg))
        #MESSAGE_LOG.append({ "type": "info", "message": str(msg) })

def warn(msg, indent="", target=None):
    if target is None: target = sys.stderr
    if STANDARD_OUTPUT:
        print("%sWARNING: %s" % (indent, str(msg)), file=target)
    MESSAGE_LOG.append({ "type": "warn", "message": str(msg) })

def err(msg, indent="", target=None):
    if target is None: target = sys.stderr
    if STANDARD_OUTPUT:
        print("%sERROR: %s" % (indent, str(msg)), file=target)
    MESSAGE_LOG.append({ "type": "error", "message": str(msg) })

def s_if_plural(count):
    return "" if count == 1 else "s"
