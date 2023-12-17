# -*- coding: utf-8 -*-

from pytest import raises

from clastic import Application, render_basic, Response
from clastic.application import Application

from clastic.route import Route
from clastic.route import (InvalidEndpoint,
                           InvalidPattern,
                           InvalidMethod)
from clastic.route import S_STRICT, S_REWRITE, S_REDIRECT
from clastic.errors import NotFound, ErrorHandler


MODES = (S_STRICT, S_REWRITE, S_REDIRECT)
NO_OP = lambda: Response()


def test_new_base_route():
    # note default slashing behavior
    ub_rp = Route('/a/b/<t:int>/thing/<das+int>', NO_OP)
    rp = ub_rp.bind(Application())
    d = rp.match_path('/a/b/1/thing/1/2/3/4')
    assert d == {u't': 1, u'das': [1, 2, 3, 4]}

    d = rp.match_path('/a/b/1/thing/hi/')
    assert d == None

    d = rp.match_path('/a/b/1/thing/')
    assert d == None

    ub_rp = Route('/a/b/<t:int>/thing/<das*int>', NO_OP, methods=['GET'])
    rp = ub_rp.bind(Application())
    d = rp.match_path('/a/b/1/thing')
    assert d == {u't': 1, u'das': []}


def test_base_route_executes():
    br = Route('/', lambda request: request['stephen']).bind(Application())
    res = br.execute({'stephen': 'laporte'})
    assert res == 'laporte'


def test_base_application_basics():
    br = Route('/', lambda request: Response('lolporte'))
    ba = Application([br])
    client = ba.get_local_client()
    res = client.get('/')
    assert res.data == b'lolporte'


def test_nonbreaking_exc():
    app = Application([('/', lambda: NotFound(is_breaking=False)),
                       ('/', lambda: 'so hot in here', render_basic)])
    client = app.get_local_client()
    resp = client.get('/')
    assert resp.status_code == 200
    assert resp.data == b'so hot in here'


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
    app = Application(routes)
    client = app.get_local_client()
    assert client.get('/api/a').data == b'api: a'
    assert client.get('/api/a/b').data == b'api: a/b'

    for i, rt in enumerate(app.routes):
        assert rt.pattern == routes[i][0]

    return


def test_create_route_order_incr():
    "tests route order when routes are added incrementally"
    routes = [('/api/<api_path+>', api, render_basic),
              ('/<one>/<two>', two_segments, render_basic),
              ('/<one>/<two>/<three>', three_segments, render_basic)]
    app = Application()
    client = app.get_local_client()
    for r in routes:
        app.add(r)
        assert client.get('/api/a').data == b'api: a'
        assert client.get('/api/a/b/').data == b'api: a/b'
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
            cur_rt = Route(cur_patt, NO_OP, slash_mode=cur_mode)
            assert cur_rt, '%s did not match' % cur_patt


def test_broken_routes():
    for cur_mode in MODES:
        for cur_patt in broken_routes:
            with raises(InvalidPattern):
                cur_rt = Route(cur_patt, NO_OP, slash_mode=cur_mode)


def test_known_method():
    rt = Route('/', NO_OP, methods=['GET'])
    assert rt
    assert 'HEAD' in rt.methods


def test_unknown_method():
    with raises(InvalidMethod):
        Route('/', NO_OP, methods=['lol'])


def test_debug_raises():
    app_nodebug = Application([('/', lambda: 1/0)], debug=False)
    client = app_nodebug.get_local_client()
    assert client.get('/').status_code == 500

    err_handler = ErrorHandler(reraise_uncaught=True)
    app_debug = Application([('/', lambda: 1/0)], error_handler=err_handler)
    client = app_debug.get_local_client()

    with raises(ZeroDivisionError):
        client.get('/')
    return


def test_slashing_behaviors():
    routes = [('/', NO_OP),
              ('/goof/spoof/', NO_OP)]
    app_strict = Application(routes, slash_mode=S_STRICT)
    app_redirect = Application(routes, slash_mode=S_REDIRECT)
    app_rewrite = Application(routes, slash_mode=S_REWRITE)

    cl_strict = app_strict.get_local_client()
    cl_redirect = app_redirect.get_local_client()
    cl_rewrite = app_rewrite.get_local_client()

    assert cl_strict.get('/').status_code == 200
    assert cl_rewrite.get('/').status_code == 200
    assert cl_redirect.get('/').status_code == 200

    assert cl_strict.get('/goof//spoof//').status_code == 404
    assert cl_rewrite.get('/goof//spoof//').status_code == 200
    assert cl_redirect.get('/goof//spoof//').status_code == 302
    assert cl_redirect.get('/goof//spoof//', follow_redirects=True).status_code == 200

    assert cl_strict.get('/dne/dne//').status_code == 404
    assert cl_rewrite.get('/dne/dne//').status_code == 404
    assert cl_redirect.get('/dne/dne//').status_code == 404
