# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.test import Client

from clastic import Response
from clastic.contrib.webtop.top import create_app


def test_webtop_basic():
    app = create_app()
    cl = Client(app, Response)

    resp = cl.get('/')
    assert 'python' in resp.get_data(True)
