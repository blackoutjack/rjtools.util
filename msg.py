
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
    print("WARNING: %s" % msg)

def err(msg):
    raise("ERROR: %s" % msg)

