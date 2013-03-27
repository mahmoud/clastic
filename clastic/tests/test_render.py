from __future__ import unicode_literals
import os
from nose.tools import eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.render import JSONRender, default_response

from common import (hello_world_str,
                    hello_world_html,
                    hello_world_ctx,
                    complex_context)

import json

_CUR_DIR = os.path.dirname(__file__)


def test_json_render(json_response=None):
    if json_response is None:
        json_response = JSONRender(dev_mode=True)
    app = Application([('/', hello_world_ctx, json_response),
                       ('/<name>/', hello_world_ctx, json_response),
                       ('/beta/<name>/', complex_context, json_response)])

    yield ok_, callable(app.routes[0]._execute)
    yield ok_, callable(app.routes[0]._render)
    c = Client(app, BaseResponse)

    resp = c.get('/')
    yield eq_, resp.status_code, 200
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'world'

    resp = c.get('/Kurt/')
    yield eq_, resp.status_code, 200
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'Kurt'

    resp = c.get('/beta/Rajkumar/')
    yield eq_, resp.status_code, 200
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'Rajkumar'
    yield ok_, resp_data['date']
    yield ok_, len(resp_data) > 4


#def test_default_json_render():
#    from clastic.render import json_response
#    for t in test_json_render(json_response):
#        yield t


def test_default_render():
    app = Application([('/', hello_world_ctx, default_response),
                       ('/<name>/', hello_world_ctx, default_response),
                       ('/text/<name>/', hello_world_str, default_response),
                       ('/html/<name>/', hello_world_html, default_response),
                       ('/beta/<name>/', complex_context, default_response)])

    yield ok_, callable(app.routes[0]._execute)
    yield ok_, callable(app.routes[0]._render)
    c = Client(app, BaseResponse)

    resp = c.get('/')  # test simple json with endpoint default
    yield eq_, resp.status_code, 200
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'world'

    resp = c.get('/Kurt/')  # test simple json with url param
    yield eq_, resp.status_code, 200
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'Kurt'

    resp = c.get('/beta/Rajkumar/')  # test fancy json
    yield eq_, resp.status_code, 200
    resp_data = json.loads(resp.data)
    yield eq_, resp_data['name'], 'Rajkumar'
    yield ok_, resp_data['date']
    yield ok_, len(resp_data) > 4

    resp = c.get('/text/Noam/')  # test text
    yield eq_, resp.status_code, 200
    yield eq_, resp.data, 'Hello, Noam!'

    resp = c.get('/html/Asia/')  # test basic html
    yield eq_, resp.status_code, 200
    yield ok_, 'text/html' in resp.headers['Content-Type']
