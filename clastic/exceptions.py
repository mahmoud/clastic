from __future__ import unicode_literals

from werkzeug.exceptions import *


def make_default_handler_map(default_400=None, default_500=None):
    ret = {}
    if default_400 and not callable(default_400):
        raise TypeError('default_400 expected function, not %r' % default_400)
    if default_500 and not callable(default_500):
        raise TypeError('default_500 expected function, not %r' % default_500)
    if default_400:
        for code in range(400, 419):
            ret[code] = default_400
    if default_500:
        for code in range(500, 504):
            ret[code] = default_500
    return ret
