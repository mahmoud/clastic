# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from clastic import Application, render_basic, GET

def _raiser():
    raise RuntimeError()


def test_nondebug_server_errors():
    app = Application([('/', _raiser, render_basic)], debug=False)
    cl = app.get_local_client()
    resps = []
    resps.append(cl.get('/', headers={'Accept': 'text/plain'}))
    resps.append(cl.get('/', headers={'Accept': 'text/html'}))
    resps.append(cl.get('/', headers={'Accept': 'application/json'}))
    resps.append(cl.get('/', headers={'Accept': 'application/xml'}))

    assert all(['RuntimeError' in r.get_data(True) for r in resps])


def test_debug_server_errors():
    app = Application([GET('/', _raiser, render_basic)], debug=True)
    cl = app.get_local_client()

    resps = []
    resps.append(cl.get('/', headers={'Accept': 'text/plain'}))
    resps.append(cl.get('/', headers={'Accept': 'text/html'}))
    resps.append(cl.get('/', headers={'Accept': 'application/json'}))
    resps.append(cl.get('/', headers={'Accept': 'application/xml'}))

    assert all(['RuntimeError' in r.get_data(True) for r in resps])


def test_debug_notfound_errors():
    app = Application([('/', _raiser, render_basic)], debug=True)
    cl = app.get_local_client()
    nf_url = '/nf'

    resps = []
    resps.append(cl.get(nf_url, headers={'Accept': 'text/plain'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'text/html'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/json'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/xml'}))

    assert all(['not found' in r.get_data(True).lower() for r in resps])


def test_nondebug_notfound_errors():
    app = Application([('/', _raiser, render_basic)], debug=True)
    cl = app.get_local_client()
    nf_url = '/nf'

    resps = []
    resps.append(cl.get(nf_url, headers={'Accept': 'text/plain'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'text/html'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/json'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/xml'}))

    assert all(['not found' in r.get_data(True).lower() for r in resps])