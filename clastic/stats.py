# -*- coding: utf-8 -*-

import time
from collections import namedtuple

from core import Application
from middleware import Middleware
from render import default_response

# TODO: what are some sane-default intervals?


class StatsMiddleware(Middleware):
    def __init__(self):
        self.hits = []
        self.per_route_resp_counts = {}
        self.per_route_perfs = {}

    def request(self, next, request, _route):
        start_time = time.time()
        pattern = _route.rule
        try:
            rt_counts = self.per_route_resp_counts[pattern]
        except KeyError:
            self.per_route_resp_counts[pattern] = rt_counts = {}
        try:
            resp = next()
            resp_type = getattr(resp, 'status_code', type(resp))
        except Exception as e:
            # see Werkzeug #388
            resp_type = getattr(e, 'code', type(e))
            raise
        finally:
            try:
                rt_counts[repr(resp_type)] += 1
            except KeyError:
                rt_counts[repr(resp_type)] = 1
            end_time = time.time()
            elapsed_time = end_time - start_time
            try:
                self.per_route_perfs[pattern].append(elapsed_time)
            except KeyError:
                self.per_route_perfs[pattern] = [elapsed_time]
        return resp


def _get_stats_dict(_application):
    try:
        stats_mw = [mw for mw in _application.middlewares
                    if isinstance(mw, StatsMiddleware)][0]
    except IndexError:
        return {'error': "StatsMiddleware doesn't seem to be installed"}
    return {'resp_counts': stats_mw.per_route_resp_counts,
            'resp_perfs': stats_mw.per_route_perfs}


def _create_app():
    routes = [('/', _get_stats_dict, default_response)]
    mws = [StatsMiddleware()]
    app = Application(routes, middlewares=mws)
    return app


if __name__ == '__main__':
    sapp = _create_app()
    sapp.serve()
