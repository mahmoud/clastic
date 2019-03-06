# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from pytest import raises

from clastic import Application
from clastic.middleware import Middleware, GetParamMiddleware
from clastic.tests.common import hello_world, hello_world_ctx, RequestProvidesName


class RenderRaisesMiddleware(Middleware):
    def render(self, next, context):
        raise RuntimeError()


def test_blank_req_provides():
    req_provides_blank = RequestProvidesName()
    app = Application([('/', hello_world)],
                      middlewares=[req_provides_blank])
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.data == b'Hello, world!'
    resp = c.get('/?name=Kurt')
    assert resp.data == b'Hello, Kurt!'


def test_req_provides():
    req_provides = RequestProvidesName('Rajkumar')
    app = Application([('/', hello_world)],
                      middlewares=[req_provides])
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.data == b'Hello, Rajkumar!'
    resp = c.get('/?name=Kurt')
    assert resp.data == b'Hello, Kurt!'


def test_get_param_mw():
    get_name_mw = GetParamMiddleware(['name', 'date'])
    app = Application([('/', hello_world)],
                      middlewares=[get_name_mw])
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.data == b'Hello, world!'
    resp = c.get('/?name=Kurt')
    assert resp.data == b'Hello, Kurt!'


def test_direct_no_render():
    render_raises_mw = RenderRaisesMiddleware()
    app = Application([('/', hello_world)],
                      middlewares=[render_raises_mw])
    c = app.get_local_client()
    resp = c.get('/')
    assert resp.data == b'Hello, world!'


def test_render_raises():
    render_raises_mw = RenderRaisesMiddleware()
    app = Application([('/', hello_world_ctx)],
                      middlewares=[render_raises_mw])
    resp = app.get_local_client().get('/')
    assert resp.status_code == 500


def test_next_in_endpoint():
    def nexter(next, request):
        return 'this endpoint is broke'

    with raises(NameError):
        Application([('/', nexter)])


def test_big_mw_stack():
    from clastic.middleware import (client_cache,
                                    compress,
                                    context,
                                    cookie,
                                    form,
                                    profile,
                                    stats,
                                    url)
    middlewares = [client_cache.HTTPCacheMiddleware(),
                   compress.GzipMiddleware(),
                   context.ContextProcessor(),
                   context.SimpleContextProcessor(),
                   cookie.SignedCookieMiddleware(),
                   form.PostDataMiddleware({'lol': str}),
                   profile.SimpleProfileMiddleware(),
                   stats.StatsMiddleware(),
                   url.ScriptRootMiddleware(),
                   url.GetParamMiddleware({})]
    [repr(mw) for mw in middlewares]
    app = Application([('/', hello_world)],
                      middlewares=middlewares)
    cl = app.get_local_client()
    resp = cl.get('/')
    assert resp.status_code == 200


def test_gzip_mw():
    from clastic.middleware import compress

    app = Application([('/<name>', hello_world)], middlewares=[compress.GzipMiddleware()])
    cl = app.get_local_client()
    resp = cl.get('/' + 'a' * 2000)
    assert resp.status_code == 200
    assert len(resp.get_data()) > 2000

    resp = cl.get('/' + 'a' * 2000, headers={'Accept-Encoding': 'gzip'})
    assert resp.status_code == 200
    assert len(resp.get_data()) < 200


def test_profile_mw():
    from clastic.middleware import profile

    app = Application([('/<name?>', hello_world)], middlewares=[profile.SimpleProfileMiddleware()])
    cl = app.get_local_client()
    resp = cl.get('/')
    assert resp.status_code == 200

    resp = cl.get('/?_prof=true')
    assert resp.status_code == 200
    resp_data = resp.get_data(True)
    assert 'function calls in 0.00' in resp_data  # e.g., 46 function calls in 0.000 seconds but that's variable/flaky
