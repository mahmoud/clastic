# -*- coding: utf-8 -*-

import json

from clastic import Application
from clastic.middleware.stats import StatsMiddleware, create_stats_app
from clastic.tests.common import hello_world


def test_stats_mw():
    app = Application([('/', hello_world),
                       ('/stats', create_stats_app())],
                      middlewares=[StatsMiddleware()])
    c = app.get_local_client()
    c.get('/')
    c.get('/')

    resp = c.get('/stats/')
    data = json.loads(resp.get_data(True))
    assert data['route_stats']['/']['200']['count'] == 2

    resp = c.post('/stats/reset')
    data = json.loads(resp.get_data(True))
    assert data['route_stats']['/']['200']['count'] == 2
    assert data['reset'] == True

    resp = c.get('/stats/')
    data = json.loads(resp.get_data(True))
    assert data['route_stats'].get('/') is None
