# -*- coding: utf-8 -*-

import os

from clastic import Application, StaticApplication, StaticFileRoute
from clastic.static import is_binary_string

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_basic_static_serve():
    static_app = StaticApplication(_CUR_DIR)
    app = Application([('/static/', static_app)])

    c = app.get_local_client()
    resp = c.get('/static/test_static.py')
    assert resp.mimetype in ('text/x-python', 'text/plain')  # text/plain on appveyor/windows for some reason
    resp = c.get('/static/does_not_exist.txt')
    assert resp.status_code == 404
    resp = c.get('/static/../core.py')
    assert resp.status_code == 403
    resp = c.get('/static/_ashes_tmpls/basic_template.html')
    assert resp.status_code == 200
    resp = c.get('/static/_ashes_tmpls/../../core.py')
    assert resp.status_code == 403

    # check that we don't navigate to root
    resp = c.get('/static//etc/hosts')
    if os.path.exists('/etc/hosts'):
        assert resp.status_code == 403
    else:
        assert resp.status_code == 404  # mostly windows


def test_binary_string():
    assert is_binary_string(b'abc') is False
    assert is_binary_string(b'5\x18.\x84\xd7F\xceR\xaf\xed\xb1\xdc\xe2VZ') is True
    assert is_binary_string(b'') is False
    assert is_binary_string((b'a' * 4096) + b'\x18') is False  # only samples so far


def test_basic_static_route():
    static_app = Application([StaticFileRoute('/source_code',
                                              _CUR_DIR + '/test_static.py')])

    c = static_app.get_local_client()
    resp = c.get('/source_code')
    assert resp.mimetype in ('text/x-python', 'text/plain')  # text/plain on appveyor/windows for some reason
    assert resp.status_code == 200
