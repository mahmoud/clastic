from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

import clastic
from clastic import Application

from common import hello_world, RequestProvidesName


def test_create_empty_application():
    app = clastic.Application()
    return app


def test_create_hw_application():
    route = ('/', hello_world)
    app = clastic.Application([route])
    yield ok_, app.routes
    yield ok_, callable(app.routes[0]._execute)
    yield ok_, app.routes[0]._bound_apps[0] is app


def test_single_mw_basic():
    dumdum = clastic.DummyMiddleware()
    app = clastic.Application([('/', hello_world)],
                              resources={},
                              middlewares=[dumdum])
    yield ok_, dumdum in app.middlewares
    yield ok_, dumdum in app.routes[0]._middlewares

    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.status_code, 200


def test_duplicate_noarg_mw():
    for mw_count in range(0, 100, 20):
        mw = [clastic.DummyMiddleware() for i in range(mw_count)]
        app = Application([('/', hello_world)],
                          middlewares=mw)
        yield ok_, app
        yield eq_, len(app.routes[0]._middlewares), mw_count

        resp = Client(app, BaseResponse).get('/')
        yield eq_, resp.status_code, 200
    return


@raises(NameError)
def test_duplicate_arg_mw():
    req_provides1 = RequestProvidesName('Rajkumar')
    req_provides2 = RequestProvidesName('Jimmy John')
    Application([('/', hello_world)],
                middlewares=[req_provides1,
                             req_provides2])


@raises(NameError)
def test_resource_builtin_conflict():
    Application(resources={'next': lambda: None})
