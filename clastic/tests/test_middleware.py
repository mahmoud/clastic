# -*- coding: utf-8 -*-


import json
import itertools

import attr
from pytest import raises

from clastic import Application, render_basic
from clastic.middleware import Middleware, GetParamMiddleware
from clastic.tests.common import hello_world, hello_world_ctx, RequestProvidesName


_CTR = itertools.count()


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
    assert 'function calls in' in resp_data  # e.g., 46 function calls in 0.000 seconds but that's variable/flaky
    assert '0.00' in resp_data # had to split this because pypy sometimes gives back "-0.000 seconds"


def test_wsgi_mw():
    @attr.s(frozen=True)
    class HeaderAddMW(object):
        header_name = attr.ib()
        header_val = attr.ib()

        def __call__(self, wsgi_app):  # TODO: should the wsgi wrapper have any access to the middleware?
            class HeaderAddWrapped(object):
                _mw = self

                def __call__(self, environ, start_response):
                    key = 'HTTP_' + self._mw.header_name
                    if key in environ:
                        environ[key] = environ[key] + '_2'
                    else:
                        environ[key] = self._mw.header_val

                    environ[key + '_CTR'] = str(next(_CTR))

                    return wsgi_app(environ, start_response)

            return HeaderAddWrapped()


    @attr.s(frozen=True)
    class WmwX(Middleware):
        wsgi_wrapper = HeaderAddMW('X', 'xxx')

    @attr.s(frozen=True)
    class WmwY(Middleware):
        wsgi_wrapper = HeaderAddMW('Y', 'yyy')


    def ep(request):
        return dict(request.headers)


    def _test_app(app):
        cl = app.get_local_client()

        resp = cl.get('/')
        assert resp.status_code == 200
        req_headers_dict = json.loads(resp.get_data())
        assert resp.status_code == 200
        assert req_headers_dict.get('X') == 'xxx'
        assert req_headers_dict.get('Y') == 'yyy'
        assert req_headers_dict.get('X-Ctr') < req_headers_dict.get('Y-Ctr')

    app = Application([('/', ep, render_basic)], middlewares=[WmwX(), WmwY()], debug=True)
    _test_app(app)

    # nest and test deduplication
    wmwx = WmwX()
    inner_app = Application([('/', ep, render_basic)], middlewares=[wmwx])
    app = Application([('/', inner_app)],
                      middlewares=[wmwx, WmwY()])
    _test_app(app)

    # now test with two matching middlewares that are separate instances
    inner_app = Application([('/', ep, render_basic)], middlewares=[WmwX()])
    app = Application([('/', inner_app)],
                      middlewares=[WmwX(), WmwY()])
    _test_app(app)
