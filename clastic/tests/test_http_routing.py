# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from nose.tools import eq_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application, render_basic
from clastic.route import GET, POST, PUT, DELETE


def test_http_method_routes():
    ep = lambda _route: repr(_route.methods)
    routes = [GET('/get', ep, render_basic),
              POST('/post', ep, render_basic),
              PUT('/put', ep, render_basic),
              DELETE('/delete', ep, render_basic)]
    app = Application(routes)
    client = Client(app, BaseResponse)
    methods = ('get', 'post', 'put', 'delete')
    status_map = {}
    for correct_method in methods:
        for attempted_method in methods:
            req_func = getattr(client, attempted_method)
            resp = req_func('/' + correct_method)
            status_code = resp.status_code
            try:
                status_map[status_code] += 1
            except KeyError:
                status_map[status_code] = 1

            if status_code == 200:
                resp_data = resp.data
                # lololol yay eval()
                route_methods = eval(resp_data) - set(['HEAD'])
                yield eq_, set([correct_method.upper()]), route_methods
    yield eq_, status_map[200], len(routes)
    yield eq_, status_map.get(405), len(routes) * (len(methods) - 1)
    return
