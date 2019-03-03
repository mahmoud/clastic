# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import json

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.middleware.stats import StatsMiddleware, create_stats_app
from clastic.tests.common import hello_world, hello_world_ctx, RequestProvidesName


def test_stats_mw():
    app = Application([('/', hello_world),
                       ('/stats', create_stats_app())],
                      middlewares=[StatsMiddleware()])
    c = Client(app, BaseResponse)
    c.get('/')
    c.get('/')

    resp = c.get('/stats/')
    data = json.loads(resp.get_data(True))
    assert data['route_stats']['/']['200']['count'] == 2
