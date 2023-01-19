#
# Utility functions for generating standardized text output.
#

import sys

DEBUG = False

def set_debug(val):
    global DEBUG
    DEBUG = val

def get_debug():
    return DEBUG

def dbg(msg):
    if DEBUG:
        print("DEBUG: %s" % msg)

def info(msg):
    print("INFO: %s" % msg)

def warn(msg):
    print("WARNING: %s" % msg, file=sys.stderr)

def err(msg):
    print("ERROR: %s" % msg, file=sys.stderr)

def s_if_plural(count):
    return "" if count == 1 else "s"

def alpha(num, lower=False):
    shift = 96 if lower else 64
    return chr(num + shift)
