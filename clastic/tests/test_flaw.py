# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.test import Client

from clastic import Response
from clastic.flaw import create_app

_EXAMPLE_TB = u"""\
Traceback (most recent call last):
  File "example.py", line 2, in <module>
    plarp
NameError: name 'plarp' is not defined
"""


def test_flaw_basic():
    app = create_app(_EXAMPLE_TB, [__file__])

    cl = Client(app, Response)

    resp = cl.get('/')
    assert resp.status_code == 200
    assert 'plarp' in resp.get_data(True)
