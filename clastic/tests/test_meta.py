# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.test import Client

from clastic import Application, render_basic, Response, MetaApplication
from clastic.middleware.cookie import SignedCookieMiddleware
from clastic.tests.common import cookie_hello_world

def test_meta_basic():
    app = Application([('/meta', MetaApplication()),
                       ('/<name?>', cookie_hello_world, render_basic)],
                      middlewares=[SignedCookieMiddleware()])
    cl = Client(app, Response)

    assert cl.get('/').status_code == 200
    assert cl.get('/meta/').status_code == 200
