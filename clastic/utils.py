# -*- coding: utf-8 -*-

from werkzeug.utils import redirect


class Redirector(object):
    """
    Meant to be used as a render step after a POST.

    partial() meets render().
    """
    def __init__(self, location, code=301):
        # TODO: make location a lamda
        self.location = location
        self.code = code

    def __call__(self):
        return redirect(self.location, code=self.code)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r, code=%r)' % (cn, self.location, self.code)


_SIZE_SYMBOLS = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
_SIZE_BOUNDS = [(1024 ** i, sym) for i, sym in enumerate(_SIZE_SYMBOLS)]
_SIZE_RANGES = zip(_SIZE_BOUNDS, _SIZE_BOUNDS[1:])


def bytes2human(nbytes, ndigits=0):
    """
    >>> bytes2human(128991)
    '126K'
    >>> bytes2human(100001221)
    '95M'
    >>> bytes2human(0, 2)
    '0.00B'
    """
    abs_bytes = abs(nbytes)
    for (size, symbol), (next_size, next_symbol) in _SIZE_RANGES:
        if abs_bytes <= next_size:
            break
    hnbytes = float(nbytes) / size
    return '{hnbytes:.{ndigits}f}{symbol}'.format(hnbytes=hnbytes,
                                                  ndigits=ndigits,
                                                  symbol=symbol)
