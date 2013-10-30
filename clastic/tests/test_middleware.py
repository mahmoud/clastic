# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import eq_, raises

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.middleware import Middleware, GetParamMiddleware
from common import hello_world, hello_world_ctx, RequestProvidesName


class RenderRaisesMiddleware(Middleware):
    def render(self, next, context):
        raise RuntimeError()


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


def test_direct_no_render():
    render_raises_mw = RenderRaisesMiddleware()
    app = Application([('/', hello_world)],
                      middlewares=[render_raises_mw])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'


def test_render_raises():
    render_raises_mw = RenderRaisesMiddleware()
    app = Application([('/', hello_world_ctx)],
                      middlewares=[render_raises_mw])
    resp = Client(app, BaseResponse).get('/')
    assert resp.status_code, 500


@raises(NameError)
def test_next_in_endpoint():
    def nexter(next, request):
        return 'this endpoint is broke'

    Application([('/', nexter)])
