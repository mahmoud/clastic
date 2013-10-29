# -*- coding: utf-8 -*-

import time
from collections import namedtuple

from application import Application
from middleware import Middleware
from render import render_basic

# TODO: what are some sane-default intervals?

Hit = namedtuple('Hit', 'start_time url pattern status_code '
                 ' elapsed_time content_type')


class StatsMiddleware(Middleware):
    def __init__(self):
        self.hits = []
        self.route_hits = {}
        self.url_hits = {}

    def request(self, next, request, _route):
        start_time = time.time()
        try:
            resp = next()
            resp_status = repr(getattr(resp, 'status_code', type(resp)))
            resp_mime_type = resp.content_type.partition(';')[0]
        except Exception as e:
            # see Werkzeug #388
            resp_status = repr(getattr(e, 'code', type(e)))
            resp_mime_type = getattr(e, 'content_type', '').partition(';')[0]
            raise
        finally:
            end_time = time.time()
            elapsed_time = end_time - start_time
            hit = Hit(start_time,
                      request.path,
                      _route.rule,
                      resp_status,
                      elapsed_time,
                      resp_mime_type)
            self.hits.append(hit)
            self.route_hits.setdefault(_route, []).append(hit)
            self.url_hits.setdefault(request.path, []).append(hit)
        return resp


from math import floor, ceil
import itertools


def hits_minutes_ago(hit_list, minutes=None):
    if minutes is None:
        minutes = 0
    start_time = time.time() - (minutes * 60)
    return itertools.dropwhile(lambda h: h.start_time < start_time, hit_list)


def hits_by_status(hit_list):
    ret = {}
    for hit in hit_list:
        try:
            ret[hit.status_code].append(hit)
        except KeyError:
            ret[hit.status_code] = [hit]
    return ret


def percentile(unsorted_data, ptile=50):
    if ptile > 100:
        raise ValueError("it's percentile, not something-else-tile")
    if not unsorted_data:
        return 0.0  # TODO: hrm, lazy
    data = sorted(unsorted_data)
    idx = (float(ptile) / 100) * len(data)
    idx_f, idx_c = int(floor(idx)), min(int(ceil(idx)), len(data) - 1)
    return (data[idx_f] + data[idx_c]) / 2.0


def mean(vals):
    if vals:
        return sum(vals, 0.0) / len(vals)
    else:
        return 0.0


def float_round(n):
    return n - (n % 2 ** -6)


def get_route_stats(rt_hits):
    ret = {}
    hbs = hits_by_status(rt_hits)
    for status, hits in hbs.items():
        ret[status] = cur = {}
        durs = [round(h.elapsed_time * 1000, 2) for h in hits]
        cur['min'] = min(durs)
        cur['max'] = max(durs)
        cur['mean'] = mean(durs)
        cur['count'] = len(durs)
        cur['median'] = percentile(durs, 50)
        cur['ninefive'] = percentile(durs, 95)
    return ret


def _get_stats_dict(_application):
    try:
        stats_mw = [mw for mw in _application.middlewares
                    if isinstance(mw, StatsMiddleware)][0]
    except IndexError:
        return {'error': "StatsMiddleware doesn't seem to be installed"}
    rt_hits = stats_mw.route_hits
    return {'resp_counts': dict([(url, len(rh)) for url, rh
                                 in stats_mw.url_hits.items()]),
            'route_stats': dict([(rt.rule, get_route_stats(rh)) for rt, rh
                                 in rt_hits.items() if rh])}


def _create_app():
    routes = [('/', _get_stats_dict, render_basic)]
    mws = [StatsMiddleware()]
    app = Application(routes, middlewares=mws)
    return app


if __name__ == '__main__':
    sapp = _create_app()
    sapp.serve()
