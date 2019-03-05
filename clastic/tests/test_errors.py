# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from pytest import raises

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, Route, render_basic, GET
from clastic.errors import BadGateway, ErrorHandler

def _raiser():
    raise RuntimeError()


def test_nondebug_server_errors():
    app = Application([('/', _raiser, render_basic)], debug=False)
    cl = Client(app, BaseResponse)
    resps = []
    resps.append(cl.get('/', headers={'Accept': 'text/plain'}))
    resps.append(cl.get('/', headers={'Accept': 'text/html'}))
    resps.append(cl.get('/', headers={'Accept': 'application/json'}))
    resps.append(cl.get('/', headers={'Accept': 'application/xml'}))

    assert all(['RuntimeError' in r.get_data(True) for r in resps])


def test_debug_server_errors():
    app = Application([GET('/', _raiser, render_basic)], debug=True)
    cl = Client(app, BaseResponse)

    resps = []
    resps.append(cl.get('/', headers={'Accept': 'text/plain'}))
    resps.append(cl.get('/', headers={'Accept': 'text/html'}))
    resps.append(cl.get('/', headers={'Accept': 'application/json'}))
    resps.append(cl.get('/', headers={'Accept': 'application/xml'}))

    assert all(['RuntimeError' in r.get_data(True) for r in resps])


def test_debug_notfound_errors():
    app = Application([('/', _raiser, render_basic)], debug=True)
    cl = Client(app, BaseResponse)
    nf_url = '/nf'

    resps = []
    resps.append(cl.get(nf_url, headers={'Accept': 'text/plain'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'text/html'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/json'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/xml'}))

    assert all(['not found' in r.get_data(True).lower() for r in resps])


def test_nondebug_notfound_errors():
    app = Application([('/', _raiser, render_basic)], debug=True)
    cl = Client(app, BaseResponse)
    nf_url = '/nf'

    resps = []
    resps.append(cl.get(nf_url, headers={'Accept': 'text/plain'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'text/html'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/json'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/xml'}))

    assert all(['not found' in r.get_data(True).lower() for r in resps])
