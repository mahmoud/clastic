# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
sys.path.append('..')  # to work out of the box in the source tree

import time
from pprint import pformat

from clastic import Application, render_basic
from clastic.middleware import GetParamMiddleware, SimpleContextProcessor
from clastic.middleware.cookie import SignedCookieMiddleware
from clastic.contrib.obj_browser import create_app as create_obj_browser_app
from clastic.contrib.webtop.top import create_app as create_webtop_app

from clastic.errors import REPLErrorHandler

def cookie_hello_world(cookie, name=None, expire_cookie=False):
    if name is None:
        name = cookie.get('name') or 'world'
    cookie['name'] = name
    if expire_cookie:
        cookie.set_expires()
    return 'Hello, %s!' % name


def see_modules(start_time, module_list, name=None):
    name = name or 'world'
    return (('Hello, %s, this app started at %s and has the following'
             ' modules available to it: \n\n%s')
            % (name, start_time, pformat(sorted(module_list))))


def debug(request, _application, _route, **kw):
    import pdb;pdb.set_trace()
    return {}


def fraiser():
    raise ValueError('what am i supposed do with these tossed errors?')


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
    get_param_names = ['name', 'date', 'session_id', 'limit', 'expire_cookie']
    middlewares = [GetParamMiddleware(get_param_names),
                   SignedCookieMiddleware(),
                   SimpleContextProcessor('name')]
    routes = [('/', cookie_hello_world, render_basic),
              ('/debug', debug, render_basic),
              ('/fizzbuzz', fizzbuzz, render_basic),
              ('/modules', see_modules, render_basic),
              ('/fraiser', fraiser, render_basic),
              ('/obj/', create_obj_browser_app()),
              ('/webtop/', create_webtop_app())]
    return Application(routes, resources, middlewares=middlewares, error_handler=REPLErrorHandler())


if __name__ == '__main__':
    create_decked_out_app().serve()
