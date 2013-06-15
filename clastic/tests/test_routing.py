from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, render_basic


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
