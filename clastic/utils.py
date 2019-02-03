# -*- coding: utf-8 -*-

import os
import time
import socket
import hashlib
import binascii
import datetime

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


def rel_datetime(d, other=None):
    # TODO: add decimal rounding factor (default 0)
    if other is None:
        other = datetime.datetime.utcnow()
    diff = other - d
    s, days = diff.seconds, diff.days
    if days > 7 or days < 0:
        return d.strftime('%d %b %y')
    elif days == 1:
        return '1 day ago'
    elif days > 1:
        return '{0} days ago'.format(diff.days)
    elif s < 5:
        return 'just now'
    elif s < 60:
        return '{0} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{0} minutes ago'.format(s / 60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{0} hours ago'.format(s / 3600)


try:
    random_hex = os.urandom(4).hex()
except AttributeError:
    # py2
    random_hex = binascii.hexlify(os.urandom(4))

_GUID_SALT = '-'.join([str(os.getpid()),
                       socket.gethostname() or '<nohostname>',
                       str(time.time()),
                       random_hex])


def int2hexguid(id_int):
    """
    I'd love to use UUID.uuid4, but this is 20x faster

    sha1 is 20 bytes. 12 bytes (96 bits) means that there's 1 in 2^32
    chance of a collision after 2^64 messages.
    """
    return hashlib.sha1((_GUID_SALT + str(id_int)).encode('utf8')).hexdigest()[:24]
