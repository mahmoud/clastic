# -*- coding: utf-8 -*-


import time

from clastic import Application, render_basic
from clastic.middleware.cookie import SignedCookieMiddleware, NEVER

from clastic.tests.common import cookie_hello_world


def test_cookie_mw():
    cookie_mw = SignedCookieMiddleware(expiry=NEVER)
    _ = repr(cookie_mw)  # coverage, lol
    app = Application([('/', cookie_hello_world, render_basic),
                       ('/<name>/', cookie_hello_world, render_basic)],
                      middlewares=[cookie_mw])
    ic = app.get_local_client()
    resp = ic.get('/')
    assert resp.status_code == 200
    assert resp.data == b'Hello, world!'
    resp = ic.get('/Kurt/')
    assert resp.data == b'Hello, Kurt!'
    resp = ic.get('/')
    assert resp.data == b'Hello, Kurt!'

    ic2 = app.get_local_client()
    resp = ic2.get('/')
    assert resp.data == b'Hello, world!'


def test_cookie_expire():
    cookie_mw = SignedCookieMiddleware(expiry=0.1)
    app = Application([('/', cookie_hello_world, render_basic),
                       ('/<name>/', cookie_hello_world, render_basic)],
                      middlewares=[cookie_mw])
    ic = app.get_local_client()
    resp = ic.get('/')
    assert resp.status_code == 200
    assert resp.data == b'Hello, world!'
    resp = ic.get('/Kurt/')
    assert resp.data == b'Hello, Kurt!'
    time.sleep(0.11)
    resp = ic.get('/')
    assert resp.data == b'Hello, world!'

    ic2 = app.get_local_client()
    resp = ic2.get('/')
    assert resp.data == b'Hello, world!'
