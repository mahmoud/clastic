# -*- coding: utf-8 -*-

import os

from clastic.contrib.webtop.top import create_app


def test_webtop_basic():
    app = create_app()
    cl = app.get_local_client()

    resp = cl.get('/')

    assert str(os.getpid()) in resp.get_data(True)
