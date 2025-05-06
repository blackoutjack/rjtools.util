from typing import TypeGuard
from numbers import Real

def get_median_of_sorted[T](vals:list[T]) -> T|float|None:
    count = len(vals)
    if count == 0: return None 

    def isFloatList(vs:list[T]) -> TypeGuard[list[float|int]]:
        # Real means float|int, so that is the isinstance check we want.
        # However, mypy type checking does not work with Real, therefore
        # use float|int in the TypeGuard.
        return all([isinstance(v, Real) for v in vals])

    if count % 2 == 1 or not isFloatList(vals):
        return vals[count//2]

    return (vals[count//2] + vals[(count-1)//2]) / 2 

def get_modes_of_sorted[T](vals:list[T]) -> list[T]|None:
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

