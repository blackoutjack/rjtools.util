

def type_error(varname, actual_typename, expected_typename):
    raise ValueError("Unexpected type for '%s': %s (expected %s)"
            % (varname, actual_typename, expected_typename))

def type_check(val, typ, varname):
    # Special case: test with the "callable" function rather than "instanceof"
    # %%% Expand to allow a list of expected types (for union types)
    if (typ == callable):
        if not callable(val):
            type_error(varname, str(type(val)), "'callable'")
    elif not isinstance(val, typ):
        type_error(varname, str(type(val)), str(typ))

