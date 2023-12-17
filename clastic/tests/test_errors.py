# -*- coding: utf-8 -*-

import json

from clastic import Application, render_basic, GET, __version__

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
    json_resp = cl.get('/', headers={'Accept': 'application/json'})
    resps.append(json_resp)
    resps.append(cl.get('/', headers={'Accept': 'application/xml'}))

    assert all(['RuntimeError' in r.get_data(True) for r in resps])
    json_data = json.loads(json_resp.get_data(True))
    assert json_data['clastic_version'] == __version__


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
    resps.append(cl.get(nf_url, headers={'Accept': 'application/xml'}))
    resps.append(cl.get(nf_url, headers={'Accept': 'application/json'}))

    assert all(['not found' in r.get_data(True).lower() for r in resps])
