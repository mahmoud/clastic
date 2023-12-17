# -*- coding: utf-8 -*-

import os

from clastic import Application, render_basic, Response
from clastic.middleware.cookie import SignedCookieMiddleware
from clastic.tests.common import cookie_hello_world


_CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_serve():
    cookie_mw = SignedCookieMiddleware()
    app = Application([('/', cookie_hello_world, render_basic),
                       ('/<name>/', cookie_hello_world, render_basic)],
                      middlewares=[cookie_mw])

    assert app.serve(_jk_just_testing=True, static_path=_CUR_DIR)
    cl = app.get_local_client()

    assert cl.get('/').status_code == 200
    assert cl.get('/static/test_serve.py').status_code == 200
