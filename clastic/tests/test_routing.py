# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse, Request

from clastic import Application, render_basic
from clastic import GET, POST, PUT, DELETE


def api(api_path):
    return 'api: %s' % api_path


def two_segments(one, two):
    return 'two_segments: %s, %s' % (one, two)


def three_segments(one, two, three):
    return 'three_segments: %s, %s, %s' % (one, two, three)


def test_create_route_order_list():
    "tests route order when routes are added as a list"
    routes = [('/api/<path:api_path>', api, render_basic),
              ('/<one>/<two>', two_segments, render_basic),
              ('/<one>/<two>/<three>', three_segments, render_basic)]
    app = Application(routes)
    client = Client(app, BaseResponse)
    yield eq_, client.get('/api/a').data, 'api: a'
    yield eq_, client.get('/api/a/b').data, 'api: a/b'

    for i, rule in enumerate(app.wmap._rules):
        yield eq_, rule.rule, routes[i][0]
    return


def test_create_route_order_incr():
    "tests route order when routes are added incrementally"
    routes = [('/api/<path:api_path>', api, render_basic),
              ('/<one>/<two>', two_segments, render_basic),
              ('/<one>/<two>/<three>', three_segments, render_basic)]
    app = Application()
    client = Client(app, BaseResponse)
    for r in routes:
        app.add(r)
        yield eq_, client.get('/api/a/b').data, 'api: a/b'
        yield eq_, app.wmap._rules[-1].rule, r[0]
    return


# test new routing

from clastic.application import BaseApplication
from clastic.routing import BaseRoute, InvalidEndpoint


def test_new_base_route():
    rp = BaseRoute('/a/b/<t:int>/thing/<das+int>')
    d = rp.match_path('/a/b/1/thing/1/2/3/4/')
    yield eq_, d, {u't': 1, u'das': [1, 2, 3, 4]}

    d = rp.match_path('/a/b/1/thing/hi/')
    yield eq_, d, None

    d = rp.match_path('/a/b/1/thing/')
    yield eq_, d, None

    rp = BaseRoute('/a/b/<t:int>/thing/<das*int>', methods=['GET'])
    d = rp.match_path('/a/b/1/thing/')
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
