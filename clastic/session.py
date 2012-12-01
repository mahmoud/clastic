from __future__ import unicode_literals
import os
from werkzeug.contrib.securecookie import SecureCookie

from middleware import Middleware
import json


class JSONCookie(SecureCookie):
    serialization_method = json


class CookieSessionMiddleware(Middleware):
    provides = ('session',)

    def __init__(self, cookie_name='clastic_session', secret_key=None):
        self.cookie_name = cookie_name
        self.secret_key = secret_key or self._get_random()

    def request(self, next, request):
        session = JSONCookie.load_cookie(request,
                                         key=self.cookie_name,
                                         secret_key=self.secret_key)

        response = next(session=session)
        session.save_cookie(response, key=self.cookie_name)
        return response

    def _get_random(self):
        return os.urandom(20)
