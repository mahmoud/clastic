# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, Route, render_basic
from clastic.errors import BadGateway


def render_error_basic(_error):
    return _error


def render_error_broken(_error):
    return 1/0


def accum_render_error(_error, request, error_list):
    if 'reraise' in request.path:
        raise _error
    if 'badgateway' in request.path:
        _error = BadGateway()
    error_list.append(_error)
    return _error


def odd_endpoint(number):
    if number % 2:
        return 'True'
    raise ValueError('not in my house')


def test_app_error_render():
    rt = Route('/<number:int>', odd_endpoint, render_basic)
    yield eq_, rt._render_error, None

    app = Application([rt], render_error=render_error_basic)
    yield eq_, rt._render_error, render_error_basic

    cl = Client(app, BaseResponse)
    yield eq_, cl.get('/1').status_code, 200

    err_resp = cl.get('/2')
    yield eq_, err_resp.status_code, 500
    yield ok_, 'not in my house' in err_resp.data

    err_resp = cl.get('/non-int')
    yield eq_, err_resp.status_code, 404


@raises(NameError)
def test_unresolved_error_render():
    rt = Route('/<number:int>', odd_endpoint, render_basic)
    Application([rt], render_error=lambda nopenope: False)


def test_broken_error_render():
    rt = Route('/<number:int>', odd_endpoint, render_basic)
    app = Application([rt], render_error=render_error_broken)
    cl = Client(app, BaseResponse)
    err_resp = cl.get('/2')
    yield eq_, err_resp.status_code, 500
    yield ok_, 'not in my house' in err_resp.data


def test_error_render_count():
    rt = Route('/<number:int>/<option?>', odd_endpoint, render_basic)
    error_list = []
    rsrc = {'error_list': error_list}
    app = Application([rt], rsrc, render_error=accum_render_error)
    cl = Client(app, BaseResponse)

    err_resp = cl.get('/39')
    yield eq_, err_resp.status_code, 200
    err_resp = cl.get('/2')
    yield eq_, err_resp.status_code, 500
    yield eq_, len(error_list), 1

    # reraising means the error will be handled by the default
    # handler, so no length change should occur
    err_resp = cl.get('/4/reraise')
    yield eq_, err_resp.status_code, 500
    yield eq_, len(error_list), 1

    err_resp = cl.get('/6/badgateway')
    yield eq_, err_resp.status_code, 502
    yield eq_, len(error_list), 2
