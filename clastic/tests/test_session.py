from __future__ import unicode_literals
from nose.tools import eq_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, render_basic
from clastic.session import CookieSessionMiddleware

from common import session_hello_world


def test_cookie_session():
    cookie_session = CookieSessionMiddleware()
    app = Application([('/', session_hello_world, render_basic),
                       ('/<name>/', session_hello_world, render_basic)],
                      middlewares=[cookie_session])
    ic = Client(app, BaseResponse)
    resp = ic.get('/')
    yield eq_, resp.status_code, 200
    yield eq_, resp.data, 'Hello, world!'
    resp = ic.get('/Kurt/')
    yield eq_, resp.data, 'Hello, Kurt!'
    resp = ic.get('/')
    yield eq_, resp.data, 'Hello, Kurt!'

    ic2 = Client(app, BaseResponse)
    resp = ic2.get('/')
    yield eq_, resp.data, 'Hello, world!'
