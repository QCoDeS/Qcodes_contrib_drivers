def items_equal(xs, ys):
    '''Compare two structures but ignore item order

    Arguments:
        xs {[type]} -- First structure
        ys {[type]} -- Second structure

    Returns:
        bool -- True if the two structures are equal when ignoring item order
    '''
    if isinstance(xs, dict) and isinstance(ys, dict):
        if len(xs) != len(ys):
            return False
        for key in xs.keys():
            try:
                if not items_equal(xs[key], ys[key]):
                    return False
            except KeyError:
                return False
        return True
    elif isinstance(xs, list) and isinstance(ys, list):
        if len(xs) != len(ys):
            return False
        sxs = xs
        sys = ys
        try:
            sxs = sorted(xs)
            sys = sorted(ys)
            for x, y in zip(sxs, sys):
                if not items_equal(x, y):
                    return False
        except TypeError:
            ys_copy = ys.copy()
            for x in xs:
                matches = [i for i, y in enumerate(ys_copy) if items_equal(x, y)]
                if len(matches):
                    del ys_copy[matches[0]]
                    continue
                else:
                    return False
        return True
    else:
        return xs == ys


def assert_items_equal(xs, ys):
    import pprint
    pp = pprint.PrettyPrinter()
    assert items_equal(xs, ys), \
        f'Difference between\n{pp.pformat(xs)}\nand\n{pp.pformat(ys)}'
