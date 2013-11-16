# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import ok_, eq_

import os
from werkzeug.test import Client

from clastic import Application, render_basic, Response
from clastic.middleware.cookie import SignedCookieMiddleware

from common import cookie_hello_world


_CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_serve():
    cookie_mw = SignedCookieMiddleware()
    app = Application([('/', cookie_hello_world, render_basic),
                       ('/<name>/', cookie_hello_world, render_basic)],
                      middlewares=[cookie_mw])

    yield ok_, app.serve(_jk_just_testing=True, static_path=_CUR_DIR)
    cl = Client(app, Response)

    yield eq_, cl.get('/').status_code, 200
    yield eq_, cl.get('/_meta/').status_code, 200
    yield eq_, cl.get('/static/test_serve.py').status_code, 200
