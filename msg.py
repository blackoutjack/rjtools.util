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

def dbg(msg, target=None):
    if DEBUG:
        if target is None: target = sys.stdout
        print("DEBUG: %s" % msg, file=target)

def info(msg, indent="", target=None):
    if target is None: target = sys.stdout
    print("%sINFO: %s" % (indent, msg), file=target)

def warn(msg, indent="", target=None):
    if target is None: target = sys.stderr
    print("%sWARNING: %s" % (indent, msg), file=target)

def err(msg, indent="", target=None):
    if target is None: target = sys.stderr
    print("%sERROR: %s" % (indent, msg), file=target)

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
