from __future__ import unicode_literals
from nose.tools import ok_

from clastic import Application, default_response
from clastic.session import CookieSessionMiddleware

from common import session_hello_world


def test_serve():
    cookie_session = CookieSessionMiddleware()
    app = Application([('/', session_hello_world, default_response),
                       ('/<name>/', session_hello_world, default_response)],
                      middlewares=[cookie_session])
    yield ok_, app.serve(_jk_just_testing=True)
