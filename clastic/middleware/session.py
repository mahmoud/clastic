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


class CookieSessionMiddleware(Middleware):
    provides = ('session',)

    def __init__(self, cookie_name='clastic_session', secret_key=None,
                 expiry=DEFAULT_EXPIRY):
        self.cookie_name = cookie_name
        self.secret_key = secret_key or self._get_random()
        self.expiry = expiry

    def request(self, next, request):
        session = JSONCookie.load_cookie(request,
                                         key=self.cookie_name,
                                         secret_key=self.secret_key)
        response = next(session=session)
        if self.expiry is not NEVER:
            # this sort of reaches into the guts of contrib.securecookie
            # so as not to involve datetime.datetime.
            session['_expires'] = time.time() + self.expiry
        session.save_cookie(response, key=self.cookie_name)
        return response

    def _get_random(self):
        return os.urandom(20)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(cookie_name=%r)' % (cn, self.cookie_name)
