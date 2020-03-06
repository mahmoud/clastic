# -*- coding: utf-8 -*-

import os
import json
import time
import base64

from secure_cookie.cookie import SecureCookie, UnquoteError

from .core import Middleware

SESSION = 0
NEVER = 'never'
NOW = 'now'
DEFAULT_EXPIRY = SESSION


class JSONCookie(SecureCookie):
    serialization_method = json

    @classmethod
    def quote(cls, value):
        ret = cls.serialization_method.dumps(value)
        ret = ret.encode('utf8')  # b64encode wants values as bytes on py3
        ret = b''.join(base64.b64encode(ret).splitlines()).strip()
        return ret

    @classmethod
    def unquote(cls, value):
        try:
            value = base64.b64decode(value)
            value = cls.serialization_method.loads(value.decode('utf8'))
        except Exception as e:
            raise UnquoteError()
        return value

    @classmethod
    def unserialize(cls, string, secret_key):
        string = string.strip('"')  # this line is for a bug in werkzeug's
                                    # test client cookie jar usage:
                                    # https://github.com/pallets/werkzeug/issues/1060
        return super(cls, JSONCookie).unserialize(string, secret_key)

    def set_expires(self, epoch_time=NOW):
        """
        epoch_time: Unix timestamp of the cookie expiry.
        """
        if epoch_time == NOW:
            epoch_time = 123456  # a day and a half after the epoch (long ago)
        self['_expires'] = epoch_time


class SignedCookieMiddleware(Middleware):
    _cookie_type = JSONCookie

    def __init__(self,
                 arg_name='cookie',
                 cookie_name=None,
                 secret_key=None,
                 domain=None,
                 path='/',
                 secure=False,
                 http_only=False,
                 expiry=SESSION,
                 data_expiry=None):
        if data_expiry is not None:
            print("SignedCookieMiddleware's data_expiry argument is deprecated"
                  ". Use expiry instead.")
            expiry = data_expiry
        self.arg_name = arg_name
        self.provides = (arg_name,)
        if cookie_name is None:
            cookie_name = 'clastic_%s' % arg_name
        self.cookie_name = cookie_name
        self.secret_key = secret_key or self._get_random()
        self.domain = domain  # used for cross-domain cookie
        self.path = path  # limit cookie to given path
        self.secure = secure  # only transmit on HTTPS
        self.http_only = http_only  # disallow client-side (js) access
        self.expiry = expiry

    def request(self, next, request):
        cookie = self._cookie_type.load_cookie(request,
                                               key=self.cookie_name,
                                               secret_key=self.secret_key)
        response = next(**{self.arg_name: cookie})
        if self.expiry != NEVER and self.expiry != SESSION:
            # let the cookie-specified value override, if present
            if '_expires' not in cookie:
                cookie['_expires'] = time.time() + self.expiry
        save_cookie_kwargs = dict(key=self.cookie_name,
                                  domain=self.domain,
                                  path=self.path,
                                  secure=self.secure,
                                  httponly=self.http_only)
        if '_expires' in cookie:
            save_cookie_kwargs['expires'] = cookie['_expires']
        cookie.save_cookie(response, **save_cookie_kwargs)
        return response

    def _get_random(self):
        return os.urandom(20)

    def __repr__(self):
        cn = self.__class__.__name__
        return ('%s(arg_name=%r, cookie_name=%r)'
                % (cn, self.arg_name, self.cookie_name))


"""# Werkzeug cookie notes:

Very messy handling around expirations. There's an expiration for the
data ('_expires' key) that doesn't necessarily correspond to the
expiration for the cookie itself. Instead, it's serialized in,
effectively presenting a cleared cookie at deserialization time,
without actually removing the cookie from the client's browser.

Then there's also 'expires' and 'session_expires' arguments to the
save_cookie and serialize methods.

There's also the max_age argument, but since IE didn't add support for
the Max-Age cookie flag forever, usage isn't really recommended
practice, to say the least.

# Clastic integration notes:

Clastic's approach to this mess has been to try and unify the
expiration interface. Not only is data expired so it won't be
serialized back in, but the best attempt is made to line up the
expiration times so the cookie is cleared from the browser.

"""
