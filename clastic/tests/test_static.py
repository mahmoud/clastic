from __future__ import unicode_literals
import os
from nose.tools import eq_

from werkzeug.test import Client
from clastic import Application, StaticApplication, Response

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_basic_static_serve():
    static_app = StaticApplication(_CUR_DIR)
    app = Application([('/static/', static_app)])

    c = Client(app, Response)
    resp = c.get('/static/test_static.py')
    yield eq_, resp.mimetype, 'text/x-python'
    resp = c.get('/static/test_static.pyc')
    yield eq_, resp.mimetype, 'application/x-python-code'
    resp = c.get('/static/does_not_exist.txt')
    yield eq_, resp.status_code, 404
    resp = c.get('/static/../core.py')
    yield eq_, resp.status_code, 403
    resp = c.get('/static/_ashes_tmpls/basic_template.html')
    yield eq_, resp.status_code, 200
    resp = c.get('/static/_ashes_tmpls/../../core.py')
    yield eq_, resp.status_code, 403
