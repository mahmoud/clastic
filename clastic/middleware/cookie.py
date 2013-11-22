# -*- coding: utf-8 -*-

import os
import json
import time

from werkzeug.contrib.securecookie import SecureCookie

from .core import Middleware


DEFAULT_EXPIRY = 3600  # 1 hour, but it's refreshed on every request
NEVER = object()


class JSONCookie(SecureCookie):
    serialization_method = json


class SignedCookieMiddleware(Middleware):
    def __init__(self,
                 arg_name='cookie',
                 cookie_name=None,
                 secret_key=None,
                 domain=None,
                 path='/',
                 secure=False,
                 http_only=False,
                 data_expiry=DEFAULT_EXPIRY,
                 cookie_expiry=None):
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
        self.data_expiry = data_expiry
        self.cookie_expiry = cookie_expiry

    def request(self, next, request):
        cookie = JSONCookie.load_cookie(request,
                                        key=self.cookie_name,
                                        secret_key=self.secret_key)
        response = next(**{self.arg_name: cookie})
        if self.data_expiry is not NEVER:
            # this sort of reaches into the guts of contrib.securecookie
            # so as not to involve datetime.datetime.
            cookie['_expires'] = time.time() + self.data_expiry
        # TODO: how to incorporate data vs cookie expiry
        cookie.save_cookie(response,
                           key=self.cookie_name,
                           domain=self.domain,
                           path=self.path,
                           secure=self.secure,
                           httponly=self.http_only)
        return response

    def _get_random(self):
        return os.urandom(20)

    def __repr__(self):
        cn = self.__class__.__name__
        return ('%s(arg_name=%r, cookie_name=%r)'
                % (cn, self.arg_name, self.cookie_name))
