# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, render_basic
from clastic.application import BaseApplication

from clastic.route import BaseRoute, Route
from clastic.route import (InvalidEndpoint,
                           InvalidPattern,
                           InvalidMethod)
from clastic.route import S_STRICT, S_REWRITE, S_REDIRECT
from clastic.errors import NotFound, ErrorHandler


MODES = (S_STRICT, S_REWRITE, S_REDIRECT)
NO_OP = lambda: BaseResponse()


def test_new_base_route():
    # note default slashing behavior
    rp = BaseRoute('/a/b/<t:int>/thing/<das+int>')
    d = rp.match_path('/a/b/1/thing/1/2/3/4')
    yield eq_, d, {u't': 1, u'das': [1, 2, 3, 4]}

    d = rp.match_path('/a/b/1/thing/hi/')
    yield eq_, d, None

    d = rp.match_path('/a/b/1/thing/')
    yield eq_, d, None

    rp = BaseRoute('/a/b/<t:int>/thing/<das*int>', methods=['GET'])
    d = rp.match_path('/a/b/1/thing')
    yield eq_, d, {u't': 1, u'das': []}


def test_base_route_executes():
    br = BaseRoute('/', lambda request: request['stephen'])
    res = br.execute({'stephen': 'laporte'})
    yield eq_, res, 'laporte'


@raises(InvalidEndpoint)
def test_base_route_raises_on_no_ep():
    BaseRoute('/a/b/<t:int>/thing/<das+int>').execute({})


def test_base_application_basics():
    br = BaseRoute('/', lambda request: BaseResponse('lolporte'))
    ba = BaseApplication([br])
    client = Client(ba, BaseResponse)
    res = client.get('/')
    yield eq_, res.data, 'lolporte'


def test_nonbreaking_exc():
    app = Application([('/', lambda: NotFound(is_breaking=False)),
                       ('/', lambda: 'so hot in here', render_basic)])
    client = Client(app, BaseResponse)
    resp = client.get('/')
    yield eq_, resp.status_code, 200
    yield eq_, resp.data, 'so hot in here'


def api(api_path):
    return 'api: %s' % '/'.join(api_path)


def two_segments(one, two):
    return 'two_segments: %s, %s' % (one, two)


def three_segments(one, two, three):
    return 'three_segments: %s, %s, %s' % (one, two, three)


def test_create_route_order_list():
    "tests route order when routes are added as a list"
    routes = [('/api/<api_path+>', api, render_basic),
              ('/<one>/<two>', two_segments, render_basic),
              ('/<one>/<two>/<three>', three_segments, render_basic)]
    app = BaseApplication(routes)
    client = Client(app, BaseResponse)
    yield eq_, client.get('/api/a').data, 'api: a'
    yield eq_, client.get('/api/a/b').data, 'api: a/b'

    for i, rt in enumerate(app.routes):
        yield eq_, rt.pattern, routes[i][0]
    return


def test_create_route_order_incr():
    "tests route order when routes are added incrementally"
    routes = [('/api/<api_path+>', api, render_basic),
              ('/<one>/<two>', two_segments, render_basic),
              ('/<one>/<two>/<three>', three_segments, render_basic)]
    app = BaseApplication()
    client = Client(app, BaseResponse)
    for r in routes:
        app.add(r)
        yield eq_, client.get('/api/a/b').data, 'api: a/b'
        yield eq_, app.routes[-1].pattern, r[0]
    return


"""
New routing testing strategy notes
==================================

* Successful endpoint
* Failing endpoint (i.e., raise a non-HTTPException exception)
* Raising endpoint (50x, 40x (breaking/nonbreaking))
* GET/POST/PUT/DELETE/OPTIONS/HEAD, etc.
"""

no_arg_routes = ['/',
                 '/alpha',
                 '/alpha/',
                 '/beta',
                 '/gamma/',
                 '/delta/epsilon',
                 '/zeta/eta/']

arg_routes = ['/<theta>',
              '/iota/<kappa>/<lambda>/mu/',
              '/<nu:int>/<xi:float>/<omicron:unicode>/<pi:str>/',
              '/<rho+>/',
              '/<sigma*>/',
              '/<tau?>/',
              '/<upsilon:>/']

broken_routes = ['alf',
                 '/bet//',
                 '/<cat->/',
                 '/<very*doge>/']


def test_ok_routes():
    ok_routes = no_arg_routes + arg_routes
    for cur_mode in MODES:
        for cur_patt in ok_routes:
            try:
                cur_rt = Route(cur_patt, NO_OP, slash_mode=cur_mode)
            except:
                yield ok_, False, cur_patt
            else:
                yield ok_, cur_rt


def test_broken_routes():
    for cur_mode in MODES:
        for cur_patt in broken_routes:
            try:
                cur_rt = Route(cur_patt, NO_OP, slash_mode=cur_mode)
            except InvalidPattern:
                yield ok_, True
            else:
                yield ok_, False, cur_rt


def test_known_method():
    rt = Route('/', NO_OP, methods=['GET'])
    yield ok_, rt
    yield ok_, 'HEAD' in rt.methods


@raises(InvalidMethod)
def test_unknown_method():
    Route('/', NO_OP, methods=['lol'])


def test_debug_raises():
    app_nodebug = Application([('/', lambda: 1/0)], debug=False)
    client = Client(app_nodebug, BaseResponse)
    yield eq_, client.get('/').status_code, 500

    err_handler = ErrorHandler(reraise_uncaught=True)
    app_debug = Application([('/', lambda: 1/0)], error_handler=err_handler)
    client = Client(app_debug, BaseResponse)
    try:
        resp = client.get('/')
    except ZeroDivisionError:
        yield ok_, True
    else:
        yield ok_, False, ('%r did not raise ZeroDivisionError (got %r)'
                           % (app_debug, resp))


def test_slashing_behaviors():
    routes = [('/', NO_OP),
              ('/goof/spoof/', NO_OP)]
    app_strict = Application(routes, slash_mode=S_STRICT)
    app_redirect = Application(routes, slash_mode=S_REDIRECT)
    app_rewrite = Application(routes, slash_mode=S_REWRITE)

    cl_strict = Client(app_strict, BaseResponse)
    cl_redirect = Client(app_redirect, BaseResponse)
    cl_rewrite = Client(app_rewrite, BaseResponse)

    yield eq_, cl_strict.get('/').status_code, 200
    yield eq_, cl_rewrite.get('/').status_code, 200
    yield eq_, cl_redirect.get('/').status_code, 200

    yield eq_, cl_strict.get('/goof//spoof//').status_code, 404
    yield eq_, cl_rewrite.get('/goof//spoof//').status_code, 200
    yield eq_, cl_redirect.get('/goof//spoof//').status_code, 302
    yield eq_, cl_redirect.get('/goof//spoof//', follow_redirects=True).status_code, 200

    yield eq_, cl_strict.get('/dne/dne//').status_code, 404
    yield eq_, cl_rewrite.get('/dne/dne//').status_code, 404
    yield eq_, cl_redirect.get('/dne/dne//').status_code, 404
