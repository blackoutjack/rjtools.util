
import sys

DEBUG = False

def set_debug(val):
    global DEBUG
    DEBUG = val

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
