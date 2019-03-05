# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from clastic import Application, render_basic, MetaApplication
from clastic.middleware.cookie import SignedCookieMiddleware
from clastic.tests.common import cookie_hello_world

def test_meta_basic():
    app = Application([('/meta', MetaApplication()),
                       ('/<name?>', cookie_hello_world, render_basic)],
                      middlewares=[SignedCookieMiddleware()])
    cl = app.get_local_client()

    assert cl.get('/').status_code == 200
    assert cl.get('/meta/').status_code == 200
