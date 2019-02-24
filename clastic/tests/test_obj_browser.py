# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

import pytest
from werkzeug.test import Client

from clastic import Response
from clastic.contrib.obj_browser import create_app


_IS_PYPY = '__pypy__' in sys.builtin_module_names


@pytest.mark.skipif(_IS_PYPY, reason='pypy gc cannot support obj browsing')
def test_flaw_basic():
    app = create_app()

    cl = Client(app, Response)

    resp = cl.get('/')
    assert resp.status_code == 302  # take me to the default
    resp = cl.get('/', follow_redirects=True)

    assert resp.status_code == 200  # default should be sys
    assert 'modules' in resp.get_data(True)
