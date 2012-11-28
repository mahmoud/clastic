from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.render import JSONRender
from common import hello_world_ctx, complex_context
import json

def test_json_render():
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
