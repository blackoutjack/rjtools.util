

def type_check(val, typ, varname):
    # Special case: test with the "callable" function rather than "instanceof".
    if (typ == callable):
        if not callable(val):
            raise ValueError("Unexpected type for %s: %r (expected callable)"
                    % (varname, type(val)))
    elif not isinstance(val, typ):
        raise ValueError("Unexpected type for %s: %r (expected %r)"
                % (varname, type(val), typ))

