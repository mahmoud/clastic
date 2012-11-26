from nose.tools import raises

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

import clastic


def hello_world():
    return clastic.Response("Hello, World")


def test_create_empty_application():
    app = clastic.Application()
    return app


def test_create_hw_application():
    route = ('/', hello_world)
    app = clastic.Application([route])
    assert app.routes
    assert callable(app.routes[0]._execute)
    assert app.routes[0]._bound_apps[0] is app
    return app


@raises(NameError)
def test_resource_builtin_conflict():
    resources = {'next': lambda: None}
    app = clastic.Application(resources=resources)
    return app


def test_single_mw_basic():
    dumdum = clastic.DummyMiddleware()
    app = clastic.Application([('/', hello_world)],
                              resources={},
                              middlewares=[dumdum])
    assert dumdum in app.middlewares
    assert dumdum in app.routes[0]._middlewares
    return app


def test_single_mw_req():
    app = test_single_mw_basic()
    c = Client(app, BaseResponse)
    resp = c.get('/')
    assert resp.status_code == 200
