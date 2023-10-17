# -*- coding: utf-8 -*-

import os
import time
import socket
import hashlib
import binascii
import datetime

from werkzeug.utils import redirect

# these utils got lifted into boltons but are kept here for backwards
# compat
from boltons.strutils import bytes2human
from boltons.timeutils import relative_time as rel_datetime


class Redirector(object):
    """
    Meant to be used as an endpoint, or a render step after a POST.
    """
    def __init__(self, location, code=301):
        self.location = location
        self.code = code

    def __call__(self):
        return redirect(self.location, code=self.code)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r, code=%r)' % (cn, self.location, self.code)



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
