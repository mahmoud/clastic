# -*- coding: utf-8 -*-

import os
import time
from werkzeug.contrib.securecookie import SecureCookie

from .core import Middleware
import json


DEFAULT_EXPIRY = 3600  # 1 hour, but it's refreshed on every request
NEVER = object()


class JSONCookie(SecureCookie):
    serialization_method = json


class SignedCookieMiddleware(Middleware):
    def __init__(self,
                 arg_name='cookie',
                 cookie_name='clastic_session',
                 secret_key=None,
                 expiry=DEFAULT_EXPIRY):
        self.arg_name = arg_name
        self.provides = (arg_name,)
        self.cookie_name = cookie_name
        self.secret_key = secret_key or self._get_random()
        self.expiry = expiry

    def request(self, next, request):
        cookie = JSONCookie.load_cookie(request,
                                        key=self.cookie_name,
                                        secret_key=self.secret_key)
        response = next(**{self.arg_name: cookie})
        if self.expiry is not NEVER:
            # this sort of reaches into the guts of contrib.securecookie
            # so as not to involve datetime.datetime.
            cookie['_expires'] = time.time() + self.expiry
        cookie.save_cookie(response, key=self.cookie_name)
        return response

    def _get_random(self):
        return os.urandom(20)

    def __repr__(self):
        cn = self.__class__.__name__
        return ('%s(arg_name=%r, cookie_name=%r)'
                % (cn, self.arg_name, self.cookie_name))
