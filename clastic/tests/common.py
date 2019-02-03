# -*- coding: utf-8 -*-

import clastic
from clastic import Middleware


def hello_world(name=None):
    if name is None:
        name = 'world'
    return clastic.Response('Hello, %s!' % name)


def hello_world_str(name=None):
    if name is None:
        name = 'world'
    return 'Hello, %s!' % name


def hello_world_html(name=None):
    if name is None:
        name = 'world'
    return '<html><body><p>Hello, <b>%s</b>!</p></body></html>' % name


def hello_world_ctx(name=None):
    if name is None:
        name = 'world'
    greeting = 'Hello, %s!' % name
    return {'name': name,
            'greeting': greeting}


def cookie_hello_world(cookie, name=None):
    if name is None:
        name = cookie.get('name') or 'world'
    cookie['name'] = name
    return 'Hello, %s!' % name


def complex_context(name=None, date=None):
    from datetime import datetime

    ret = hello_world_ctx(name)
    if date is None:
        date = datetime.utcnow()
    ret['date'] = date
    ret['example_middleware'] = RequestProvidesName
    ret['a_lambda'] = lambda x: None
    ret['true'] = True
    ret['bool_vals'] = set([True, False])
    the_locals = dict(locals())
    the_locals.pop('ret')
    ret['the_locals'] = the_locals
    return ret


class RequestProvidesName(Middleware):
    provides = ('name',)

    def __init__(self, default_name=None):
        self.default_name = default_name

    def request(self, next, request):
        try:
            ret = next(request.args.get('name', self.default_name))
        except Exception as e:
            print(e)
            raise
        return ret


class DummyMiddleware(Middleware):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def request(self, next, request):
        name = '%s (%s)' % (self.__class__.__name__, id(self))
        if self.verbose:
            print(name, '- handling', id(request))
        try:
            ret = next()
        except Exception as e:
            if self.verbose:
                print(name, '- uhoh:', repr(e))
            raise
        if self.verbose:
            print(name, '- hooray:', repr(ret))
        return ret
