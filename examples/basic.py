# -*- coding: utf-8 -*-

import sys
sys.path.append('..')  # to work out of the box in the source tree

import time
from pprint import pformat

from clastic import Application, render_basic
from clastic.middleware import GetParamMiddleware, SimpleContextProcessor
from clastic.middleware.cookie import SignedCookieMiddleware


def cookie_hello_world(cookie, name=None):
    if name is None:
        name = cookie.get('name') or 'world'
    cookie['name'] = name
    return 'Hello, %s!' % name


def see_modules(start_time, module_list, name=None):
    name = name or 'world'
    return (('Hello, %s, this app started at %s and has the following'
             ' modules available to it: \n\n%s')
            % (name, start_time, pformat(sorted(module_list))))


def debug(request, _application, _route, **kw):
    import pdb;pdb.set_trace()
    return {}


def fizzbuzz(limit):
    """\
    Use ?limit=n to set the limit. See http://rosettacode.org/wiki/FizzBuzz for more info.
    """
    ret = []
    limit = limit or 15
    for i in xrange(1, int(limit) + 1):
        if i % 15 == 0:
            ret.append("FizzBuzz")
        elif i % 3 == 0:
            ret.append("Fizz")
        elif i % 5 == 0:
            ret.append("Buzz")
        else:
            ret.append(str(i))
    return ret


def create_decked_out_app():
    resources = {'start_time': time.time(),
                 'module_list': sys.modules.keys()}
    middlewares = [GetParamMiddleware(['name', 'date', 'session_id', 'limit']),
                   SignedCookieMiddleware(),
                   SimpleContextProcessor('name')]
    routes = [('/', cookie_hello_world, render_basic),
              ('/debug', debug, render_basic),
              ('/fizzbuzz', fizzbuzz, render_basic),
              ('/modules/', see_modules, render_basic)]
    return Application(routes, resources, middlewares=middlewares)


if __name__ == '__main__':
    create_decked_out_app().serve()
