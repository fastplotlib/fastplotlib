import numpy as np


def generate_slice_indices(kind: int):
    n_elements = 10
    a = np.arange(n_elements)

    match kind:
        case 0:
            # simplest, just int
            s = 2
            indices = [2]

        case 1:
            # everything
            s = slice(None, None, None)
            indices = list(range(10))

        case 2:
            # positive continuous range
            s = slice(1, 5, None)
            indices = [1, 2, 3, 4]

        case 3:
            # positive stepped range
            s = slice(2, 8, 2)
            indices = [2, 4, 6]

        case 4:
            # negative continuous range
            s = slice(-5, None, None)
            indices = [5, 6, 7, 8, 9]

        case 5:
            # negative backwards
            s = slice(-5, None, -1)
            indices = [5, 4, 3, 2, 1, 0]

        case 5:
            # negative backwards stepped
            s = slice(-5, None, -2)
            indices = [5, 3, 1]

        case 6:
            # negative stepped forward
            s = slice(-5, None, 2)
            indices = [5, 7, 9]

        case 7:
            # both negative
            s = slice(-8, -2, None)
            indices = [2, 3, 4, 5, 6, 7]

        case 8:
            # both negative and stepped
            s = slice(-8, -2, 2)
            indices = [2, 4, 6]

        case 9:
            # positive, negative, negative
            s = slice(8, -9, -2)
            indices = [8, 6, 4, 2]

        case 10:
            # only stepped forward
            s = slice(None, None, 2)
            indices = [0, 2, 4, 6, 8]

        case 11:
            # only stepped backward
            s = slice(None, None, -3)
            indices = [9, 6, 3, 0]

        case 12:
            # list indices
            s = [2, 5, 9]
            indices = [2, 5, 9]

        case 13:
            # bool indices
            s = a > 5
            indices = [6, 7, 8, 9]

        case 14:
            # list indices with negatives
            s = [1, 4, -2]
            indices = [1, 4, 8]

        case 15:
            # array indices
            s = np.array([1, 4, -7, 9])
            indices = [1, 4, 3, 9]

    others = [i for i in a if i not in indices]

    offset, size = (min(indices), np.ptp(indices) + 1)

    return {"slice": s, "indices": indices, "others": others, "offset": offset, "size": size}
