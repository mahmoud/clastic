# -*- coding: utf-8 -*-

from clastic.flaw import create_app

_EXAMPLE_TB = u"""\
Traceback (most recent call last):
  File "example.py", line 2, in <module>
    plarp
NameError: name 'plarp' is not defined
"""


def test_flaw_basic():
    app = create_app(_EXAMPLE_TB, [__file__])

    cl = app.get_local_client()

    resp = cl.get('/')
    assert resp.status_code == 200
    assert 'plarp' in resp.get_data(True)
