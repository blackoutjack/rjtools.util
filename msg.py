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

def info(msg, indent=""):
    print("%sINFO: %s" % (indent, msg))

def warn(msg, indent=""):
    print("%sWARNING: %s" % (indent, msg), file=sys.stderr)

def err(msg, indent=""):
    print("%sERROR: %s" % (indent, msg), file=sys.stderr)

def s_if_plural(count):
    return "" if count == 1 else "s"

# %%% Handle cases where num > 26 (return "AA", "AB" and so forth)
def alpha(num, lower=False):
    shift = 96 if lower else 64
    return chr(num + shift)
