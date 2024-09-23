

'''Emptiness test meant for possibly-None strings'''
def empty(value):
    return value in [None, '', []]

def nonempty(value):
    return not empty(value)

def type_error(varname, actual_typename, expected_typename):
    raise ValueError("Unexpected type for '%s': %s (expected %s)"
            % (varname, actual_typename, expected_typename))

def has_type(val, typ):
    if typ == callable:
        # Special case: check if `val` is "callable" (not technically a type)
        return callable(val)
    if typ is None:
        return val is None
    return isinstance(val, typ)

def type_check(val, typ, varname):
    if isinstance(typ, list):
        # Check that `val` is a list of values with the type that `typ` contains
        if not has_type(val, list):
            type_error(varname, str(type(val)), "list")
        for index, subval in enumerate(val):
            ok = False
            for t in typ:
                if has_type(subval, t):
                    ok = True
                    break
            if not ok:
                type_error(
                    "%s[%d]" % (varname, index),
                    str(type(subval)),
                    " or ".join([str(t) for t in typ]))
    elif not has_type(val, typ):
        type_error(varname, str(type(val)), str(typ))

