# -*- coding: utf-8 -*-

import time
from collections import namedtuple

from boltons.statsutils import Stats
from boltons.iterutils import bucketize

from ..application import Application
from ..render import render_basic
from .core import Middleware


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
                      _route.pattern,
                      resp_status,
                      elapsed_time,
                      resp_mime_type)
            self.hits.append(hit)
            self.route_hits.setdefault(_route, []).append(hit)
            self.url_hits.setdefault(request.path, []).append(hit)
        return resp


def _get_route_stats(rt_hits):
    ret = {}
    hits_by_status = bucketize(rt_hits, 'status_code')
    for status, hits in hits_by_status.items():
        ret[status] = cur = {}
        durs = [round(h.elapsed_time * 1000, 2) for h in hits]
        stats = Stats(durs, use_copy=False)
        desc_dict = stats.describe(quantiles=[0.25, 0.5, 0.75, 0.95, 0.99], format="dict")
        cur.update(desc_dict)
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
            'route_stats': dict([(rt.pattern, _get_route_stats(rh)) for rt, rh
                                 in rt_hits.items() if rh])}


if __name__ == '__main__':
    routes = [('/', _get_stats_dict, render_basic)]
    mws = [StatsMiddleware()]
    app = Application(routes, middlewares=mws)

    app.serve()
