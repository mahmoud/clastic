# -*- coding: utf-8 -*-

import os
import sys
import json

from clastic import Application, render_basic, StaticFileRoute, MetaApplication
from clastic.middleware.cookie import SignedCookieMiddleware
from clastic.tests.common import cookie_hello_world

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
IS_PYPY = '__pypy__' in sys.builtin_module_names


def test_meta_basic():
    app = Application([('/meta', MetaApplication()),
                       ('/<name?>', cookie_hello_world, render_basic),
                       StaticFileRoute('/', _CUR_DIR + '/test_meta.py')],
                      middlewares=[SignedCookieMiddleware()])
    cl = app.get_local_client()

    assert cl.get('/').status_code == 200
    assert cl.get('/meta/').status_code == 200


def test_route_names():
    # function, built-in function, method, callable object
    # method StaticFileRoute and StaticApp

    def func_ep(request):
        return repr(request)

    class CallableObj(object):
        def __init__(self, greet):
            self.greet = greet

        def __call__(self, request):
            return self.greet

        def ep_method(self):
            return self.greet

    obj = CallableObj('hi')
    routes = [('/func', func_ep, render_basic),
              ('/method', obj.ep_method, render_basic),
              ('/callable_obj', obj, render_basic),
              StaticFileRoute('/file', _CUR_DIR + '/test_meta.py'),
              ('/meta', MetaApplication())]
    if not IS_PYPY:
        routes.append(('/builtin', sum, render_basic))

    app = Application(routes=routes,
                      resources={'iterable': [1, 2, 3], 'start': 0})

    cl = app.get_local_client()
    assert cl.get('/meta/').status_code == 200
    if IS_PYPY:
        return

    resp = cl.get('/meta/json/')
    assert resp.status_code == 200

    endpoints = [r['endpoint'] for r in json.loads(resp.data)['app']['routes']]
    assert endpoints == [{'module_name': 'clastic.tests.test_meta', 'name': 'func_ep'},
                         {'module_name': 'clastic.tests.test_meta.CallableObj', 'name': 'ep_method'},
                         {'module_name': 'clastic.tests.test_meta', 'name': 'CallableObj'},
                         {'module_name': 'clastic.static.StaticFileRoute', 'name': 'get_file_response'},
                         {'module_name': 'clastic.meta.MetaApplication', 'name': 'get_main'},
                         {'module_name': 'clastic.static.StaticApplication',
                          'name': 'get_file_response'},
                         {'module_name': 'clastic.meta.MetaApplication', 'name': 'get_main'},
                         {'module_name': 'builtins', 'name': 'sum'}]


def test_resource_redaction():
    app = Application(routes=[('/meta', MetaApplication())],
                      resources={'a_secret': 'vsecret', 'ok': 'bokay'})

    cl = app.get_local_client()
    resp = cl.get('/meta/')
    assert resp.status_code == 200

    content = resp.get_data(as_text=True)
    assert 'bokay' in content
    assert 'vsecret' not in content
