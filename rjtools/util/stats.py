from numbers import Real
from typing import Optional, Union, cast

def get_median_of_sorted[T](vals:list[T]) -> Optional[Union[T,float]]:
    count = len(vals)
    if count == 0: return None 

    if count % 2 == 1 or not all([isinstance(v, Real) for v in vals]):
        return vals[count//2]
    numvals = cast(list[float], vals)

    return (numvals[count//2] + numvals[(count-1)//2]) / 2 

def get_modes_of_sorted[T](vals:list[T]) -> Optional[list[T]]:
    if len(vals) == 0: return None 

    modes = []
    maxtimes = 0
    last = vals[0]
    times = 1
    for val in vals[1:]:
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

