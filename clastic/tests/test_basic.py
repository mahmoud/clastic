# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic.application import Application

from common import hello_world, DummyMiddleware, RequestProvidesName


def test_create_empty_application():
    app = Application()
    return app


def test_create_hw_application():
    route = ('/', hello_world)
    app = Application([route])
    yield ok_, app.routes
    yield ok_, callable(app.routes[0]._execute)
    yield ok_, app.routes[0]._bound_apps[0] is app


def test_single_mw_basic():
    dumdum = DummyMiddleware()
    app = Application([('/', hello_world)],
                      resources={},
                      middlewares=[dumdum])
    yield ok_, dumdum in app.middlewares
    yield ok_, dumdum in app.routes[0]._middlewares

    resp = Client(app, BaseResponse).get('/')
    yield eq_, resp.status_code, 200


def test_duplicate_noarg_mw():
    for mw_count in range(0, 100, 20):
        mw = [DummyMiddleware() for i in range(mw_count)]
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


def test_subapplication_basic():
    dum1 = DummyMiddleware()
    dum2 = DummyMiddleware()
    no_name_app = Application([('/', hello_world)],
                              middlewares=[dum1])
    name_app = Application([('/', hello_world),
                            ('/foo', hello_world)],
                           resources={'name': 'Rajkumar'},
                           middlewares=[dum1])
    app = Application([('/', no_name_app),
                       ('/beta/', name_app)],
                      resources={'name': 'Kurt'},
                      middlewares=[dum2])

    yield eq_, len(app.routes), 3

    merged_name_app_patts = [r.pattern for r in app.routes
                             if r.pattern.startswith('/beta')]
    name_app_patts = [r.pattern for r in name_app.routes]

    def check_patts(app_patts, subapp_patts):
        assert all(a.endswith(s) for a, s in zip(app_patts, subapp_patts))

    # should be the same order as name_app
    yield eq_, len(merged_name_app_patts), len(name_app_patts)
    yield check_patts, merged_name_app_patts, name_app_patts

    yield eq_, len(set([r.pattern for r in app.routes])), 3
    yield eq_, len(app.routes[0]._middlewares), 1  # middleware merging

    resp = Client(no_name_app, BaseResponse).get('/')
    yield eq_, resp.data, 'Hello, world!'
    resp = Client(name_app, BaseResponse).get('/')
    yield eq_, resp.data, 'Hello, Rajkumar!'
    resp = Client(app, BaseResponse).get('/')
    yield eq_, resp.data, 'Hello, Kurt!'
    resp = Client(app, BaseResponse).get('/beta/')
    yield eq_, resp.data, 'Hello, Kurt!'
    resp = Client(app, BaseResponse).get('/beta/foo')
    yield eq_, resp.data, 'Hello, Kurt!'
    resp = Client(app, BaseResponse).get('/larp4lyfe/')
    yield eq_, resp.status_code, 404
