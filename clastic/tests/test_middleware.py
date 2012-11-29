from __future__ import unicode_literals
from nose.tools import eq_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.middleware import GetParamMiddleware
from common import hello_world, RequestProvidesName


def test_blank_req_provides():
    req_provides_blank = RequestProvidesName()
    app = Application([('/', hello_world)],
                      middlewares=[req_provides_blank])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'
    resp = c.get('/?name=Kurt')
    yield eq_, resp.data, 'Hello, Kurt!'


def test_req_provides():
    req_provides = RequestProvidesName('Rajkumar')
    app = Application([('/', hello_world)],
                      middlewares=[req_provides])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, Rajkumar!'
    resp = c.get('/?name=Kurt')
    yield eq_, resp.data, 'Hello, Kurt!'


def test_get_param_mw():
    get_name_mw = GetParamMiddleware(['name', 'date'])
    app = Application([('/', hello_world)],
                      middlewares=[get_name_mw])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'
    resp = c.get('/?name=Kurt')
    yield eq_, resp.data, 'Hello, Kurt!'
