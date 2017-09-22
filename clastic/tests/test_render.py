# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import json

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.render import (JSONRender,
                            JSONPRender,
                            render_basic,
                            BasicRender,
                            Table,
                            TabularRender)

from clastic.tests.common import (hello_world_str,
                                  hello_world_html,
                                  hello_world_ctx,
                                  complex_context)


_CUR_DIR = os.path.dirname(__file__)


def test_json_render(render_json=None):
    if render_json is None:
        render_json = JSONRender(dev_mode=True)
    app = Application([('/', hello_world_ctx, render_json),
                       ('/<name>/', hello_world_ctx, render_json),
                       ('/beta/<name>/', complex_context, render_json)])

    assert callable(app.routes[0]._execute)
    assert callable(app.routes[0]._render)
    c = Client(app, BaseResponse)

    resp = c.get('/')
    assert resp.status_code == 200
    resp_data = json.loads(resp.data)
    assert resp_data['name'] == 'world'

    resp = c.get('/Kurt/')
    assert resp.status_code == 200
    resp_data = json.loads(resp.data)
    assert resp_data['name'] == 'Kurt'

    resp = c.get('/beta/Rajkumar/')
    assert resp.status_code == 200
    resp_data = json.loads(resp.data)
    assert resp_data['name'] == 'Rajkumar'
    assert resp_data['date']
    assert len(resp_data) > 4


def test_jsonp_render(render_json=None):
    if render_json is None:
        render_json = JSONPRender(qp_name='callback', dev_mode=True)
    app = Application([('/', hello_world_ctx, render_json),
                       ('/<name>/', hello_world_ctx, render_json),
                       ('/beta/<name>/', complex_context, render_json)])

    c = Client(app, BaseResponse)

    resp = c.get('/?callback=test_callback')
    assert resp.status_code == 200
    assert resp.data.startswith('test_callback')
    assert 'world' in resp.data

    resp = c.get('/?callback=test_callback')
    assert resp.status_code == 200
    assert resp.data.startswith('test_callback')
    assert 'world' in resp.data

#def test_default_json_render():
#    from clastic.render import render_json
#    for t in test_json_render(render_json):
#        yield t


def test_default_render():
    app = Application([('/', hello_world_ctx, render_basic),
                       ('/<name>/', hello_world_ctx, render_basic),
                       ('/text/<name>/', hello_world_str, render_basic),
                       ('/html/<name>/', hello_world_html, render_basic),
                       ('/beta/<name>/', complex_context, render_basic)])

    assert callable(app.routes[0]._execute)
    assert callable(app.routes[0]._render)
    c = Client(app, BaseResponse)

    resp = c.get('/')  # test simple json with endpoint default
    assert resp.status_code == 200
    resp_data = json.loads(resp.data)
    assert resp_data['name'] == 'world'

    resp = c.get('/Kurt/')  # test simple json with url param
    assert resp.status_code == 200
    resp_data = json.loads(resp.data)
    assert resp_data['name'] == 'Kurt'

    resp = c.get('/beta/Rajkumar/')  # test fancy json
    assert resp.status_code == 200
    resp_data = json.loads(resp.data)
    assert resp_data['name'] == 'Rajkumar'
    assert resp_data['date']
    assert len(resp_data) > 4

    resp = c.get('/text/Noam/')  # test text
    assert resp.status_code == 200
    assert resp.data == 'Hello, Noam!'

    resp = c.get('/html/Asia/')  # test basic html
    assert resp.status_code == 200
    assert 'text/html' in resp.headers['Content-Type']


def test_custom_table_render():
    class BoldHTMLTable(Table):
        def get_cell_html(self, value):
            std_html = super(BoldHTMLTable, self).get_cell_html(value)
            return '<b>' + std_html + '</b>'

    custom_tr = TabularRender(table_type=BoldHTMLTable)
    custom_render = BasicRender(tabular_render=custom_tr)
    app = Application([('/', hello_world_ctx, custom_render)])
    c = Client(app, BaseResponse)

    resp = c.get('/?format=html')
    assert resp.status_code == 200
    assert '<b>' in resp.data
