# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.test import Client

from clastic import Application, render_basic, Response, MetaApplication
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

    assert cl.get('/').status_code == 200
