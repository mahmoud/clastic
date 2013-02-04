from __future__ import unicode_literals

from werkzeug.exceptions import *


def make_error_handler_map(handler_map=None,
                           default_400=None,
                           default_500=None):
    handler_map = dict(handler_map or {})
    ret = {}
    if default_400:
        if not callable(default_400):
            raise TypeError('default_400 expected function, not %r'
                            % default_400)
        for code in range(400, 419):
            ret[code] = default_400

    if default_500:
        if not callable(default_500):
            raise TypeError('default_500 expected function, not %r'
                            % default_500)
        for code in range(500, 504):
            ret[code] = default_500

    if handler_map:
        for code, handler in handler_map.items():
            if not callable(handler):
                raise TypeError('error %s handler expected function, not %r'
                                % (code, default_500))
            ret[code] = handler

    return ret
