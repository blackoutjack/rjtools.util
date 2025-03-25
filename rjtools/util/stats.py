from numbers import Real

def get_median_of_sorted(vals:list):
    count = len(vals)
    if count == 0: return None 

    if count % 2 == 1 or not all([isinstance(v, Real) for v in vals]):
        return vals[count//2]

    return (vals[count//2] + vals[(count-1)//2]) / 2 

def get_modes_of_sorted(vals:list):
    if len(vals) == 0: return None 

    modes = []
    maxtimes = 0
    last = None
    times = 0
    for val in vals:
        if last is None: last = val

        if val == last:
            times += 1
        else:
            if times > maxtimes:
                maxtimes = times
                modes = [last]
            elif times == maxtimes:
                modes.append(last)
            times = 1
            last = val

    if times > maxtimes:
        modes = [last]
    elif times == maxtimes:
        modes.append(last)

    return modes

