from __future__ import unicode_literals

from nose.tools import ok_, eq_, raises

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from common import hello_world, RequestProvidesName
from clastic.errors import (make_error_handler_map,
                            BadGateway,
                            Forbidden)

def exc_endpoint():
    raise RuntimeError()


def err_502_endpoint():
    raise BadGateway()


def err_403_endpoint():
    raise Forbidden()


def_err_handlers = make_error_handler_map(default_400=hello_world,
                                          default_500=hello_world,
                                          default_exc=hello_world)


def test_404():
    app = Application([], error_handlers={404: hello_world})
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'
    resp = c.get('/hi/hello/?name=Kurt')
    yield eq_, resp.data, 'Hello, world!'


def test_def_handlers():
    app = Application([('/exc/', exc_endpoint),
                       ('/502/', err_502_endpoint),
                       ('/403/', err_403_endpoint)],
                      error_handlers=def_err_handlers)
    c = Client(app, BaseResponse)
    resp = c.get('/')
    resp = c.get('/')
    yield eq_, resp.data, 'Hello, world!'
    resp = c.get('/exc/')
    yield eq_, resp.data, 'Hello, world!'
    resp = c.get('/502/')
    yield eq_, resp.data, 'Hello, world!'
    resp = c.get('/403/')
    yield eq_, resp.data, 'Hello, world!'
