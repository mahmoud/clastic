# -*- coding: utf-8 -*-

from pytest import raises

from clastic import Application, Route, render_basic
from clastic.errors import BadGateway, ErrorHandler


def odd_endpoint(number):
    if number % 2:
        return 'True'
    raise ValueError('not in my house')


def test_app_error_render():

    rt = Route('/<number:int>', odd_endpoint, render_basic)

    app = Application([rt])

    cl = app.get_local_client()
    assert cl.get('/1').status_code == 200

    err_resp = cl.get('/2')
    assert err_resp.status_code == 500
    assert b'not in my house' in err_resp.data

    err_resp = cl.get('/non-int')
    assert err_resp.status_code == 404


def test_unresolved_error_render():
    class BadErrorHandler(ErrorHandler):
        def render_error(self, nopenope, **kwargs):
            return False

    rt = Route('/<number:int>', odd_endpoint, render_basic)

    with raises(NameError):
        Application([rt], error_handler=BadErrorHandler())


def test_broken_error_render():
    class BrokenErrorHandler(ErrorHandler):
        def render_error(self, **kwargs):
            1/0

    rt = Route('/<number:int>', odd_endpoint, render_basic)
    app = Application([rt], error_handler=BrokenErrorHandler())
    cl = app.get_local_client()
    err_resp = cl.get('/2')
    assert err_resp.status_code == 500
    assert b'not in my house' in err_resp.data


def test_error_render_count():

    class AccumErrorHandler(ErrorHandler):
        def render_error(self, _error, request, error_list, **kwargs):
            if 'reraise' in request.path:
                raise _error
            if 'badgateway' in request.path:
                _error = BadGateway()
            error_list.append(_error)
            return _error

    rt = Route('/<number:int>/<option?>', odd_endpoint, render_basic)
    error_list = []
    rsrc = {'error_list': error_list}
    app = Application([rt], rsrc, error_handler=AccumErrorHandler())
    cl = app.get_local_client()

    err_resp = cl.get('/39')
    assert err_resp.status_code == 200
    err_resp = cl.get('/2')
    assert err_resp.status_code == 500
    assert len(error_list) == 1

    # reraising means the error will be handled by the default
    # handler, so no length change should occur
    err_resp = cl.get('/4/reraise')
    assert err_resp.status_code == 500
    assert len(error_list) == 1

    err_resp = cl.get('/6/badgateway')
    assert err_resp.status_code == 502
    assert len(error_list) == 2


def test_invalid_wsgi_wrapper():
    class InvalidWSGIWrapperEH(ErrorHandler):
        wsgi_wrapper = lambda app: lambda environ, nope: 'lol'

    with raises(TypeError):
        Application([], error_handler=InvalidWSGIWrapperEH())


def test_uncallable_wsgi_wrapper():
    class UncallableWSGIWrapperEH(ErrorHandler):
        wsgi_wrapper = "this should be a callable but isn't"

    with raises(TypeError):
        Application([], error_handler=UncallableWSGIWrapperEH())
