# -*- coding: utf-8 -*-

import time
import random
import datetime
from collections import namedtuple, defaultdict

from boltons.statsutils import Stats
from boltons.iterutils import bucketize

from ..route import POST
from ..application import Application
from ..render import render_basic
from ..errors import NotImplemented
from .core import Middleware


def fast_randint(start, stop):
    """Assumes you know what you're doing, unlike random.randint() which
    is pretty slow with all of its aggressive checking. See random.py
    or this post for more:
    https://eli.thegreenplace.net/2018/slow-and-fast-methods-for-generating-random-integers-in-python/

    Specifically assumes:
      * start and stop are ints
      * start < stop

    Ubuntu 16.04, CPy2.7.11+
    This func: 1000000 loops, best of 3: 0.288 usec per loop
    random.randint: 1000000 loops, best of 3: 0.785 usec per loop
    """
    return (start + int(random.random() * (stop + 1 - start)))


class Reservoir(object):
    def __init__(self, cap=True, data=None, container=None):
        if cap is True:
            self._cap = 2 ** 14  # 16k
        elif cap is False:
            self._cap = float('inf')
        else:
            self._cap = int(cap)
        if container is None:
            container = []
        self._data = container
        self._total_count = len(container)
        assert self._total_count < self._cap, 'initial count %r must be lower than cap %r' % (self._total_count, self._cap)

        for val in (data or []):
            self.add(val)
        return

    @property
    def total_count(self):
        return self._total_count

    def add(self, val):
        self._total_count += 1
        if self._total_count <= self._cap:
            self._data.append(val)
            return

        idx = fast_randint(0, self._total_count)
        if idx < self._cap:
            self._data[idx] = val
        return

    def __iter__(self):
        return iter(self._data)

    def to_list(self):
        return list(self)

    def resize(self, new_size):
        self._cap = new_size
        if new_size >= len(self._data):
            return
        self._data = self._data[:new_size]

    def __repr__(self):
        cn = self.__class__.__name__
        return ('<%s cap=%r, data_count=%r, total_count=%r>'
                % (cn, self._cap, len(self._data), self._total_count))


Hit = namedtuple('Hit', 'start_time url pattern status_code '
                 ' duration content_type')


class RouteStatReservoir(Reservoir):
    def __init__(self):
        self.last_hit = None
        self.total_duration = 0.0
        super(RouteStatReservoir, self).__init__()

    def add(self, hit):
        super(RouteStatReservoir, self).add(hit)
        self.last_hit = hit.start_time
        self.total_duration += hit.duration


class StatsMiddleware(Middleware):
    def __init__(self):
        self.reset()

    def reset(self):
        self.route_hits = defaultdict(lambda: defaultdict(RouteStatReservoir))
        self.last_reset = datetime.datetime.utcnow()

    def request(self, next, request, _route):
        start_time = time.time()
        try:
            resp = next()
            resp_status = repr(getattr(resp, 'status_code', resp.__class__.__name__))
            resp_mime_type = resp.content_type.partition(';')[0]
        except Exception as e:
            # see Werkzeug #388
            resp_status = repr(getattr(e, 'code', e.__class__.__name__))
            resp_mime_type = getattr(e, 'content_type', '').partition(';')[0]
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            hit = Hit(start_time,
                      request.path,
                      _route.pattern,
                      resp_status,
                      duration,
                      resp_mime_type)
            self.route_hits[_route][resp_status].add(hit)
        return resp


def _get_route_stats(rt_hits):
    ret = {}
    for status, hits in rt_hits.items():
        ret[status] = cur = {}
        durs = [round(h.duration * 1000, 2) for h in hits]
        stats = Stats(durs, use_copy=False)
        desc_dict = stats.describe(quantiles=[0.25, 0.5, 0.75, 0.95, 0.99], format="dict")
        desc_dict['count'] = hits.total_count  # need to account for reservoir count
        desc_dict['last_hit'] = datetime.datetime.fromtimestamp(hits.last_hit).isoformat()
        desc_dict['total_duration'] = round(hits.total_duration * 1000, 2)
        cur.update(desc_dict)
    return ret


def _get_stats_mw(_application):
    try:
        stats_mw = [mw for mw in _application.middlewares
                    if isinstance(mw, StatsMiddleware)][0]
    except IndexError:
        raise NotImplemented("StatsMiddleware not installed on app %r" % _application)
    return stats_mw


def get_stats_dict(_application):
    """This endpoint provides a summary view of endppoint performance,
    broken down by URL pattern and status code or exception.

    Add ?format=json to the URL to get machine-readable data.
    """
    stats_mw = _get_stats_mw(_application)
    rt_hits = stats_mw.route_hits
    utcnow = datetime.datetime.utcnow().isoformat()
    return {'route_stats': dict([(rt.pattern, _get_route_stats(rh)) for rt, rh
                                 in rt_hits.items() if rh]),
            'start_time_utc': stats_mw.last_reset.isoformat(),
            'cur_time_utc': utcnow}


def get_and_reset_stats_dict(_application):
    ret = get_stats_dict(_application)
    stats_mw = _get_stats_mw(_application)
    stats_mw.reset()
    ret['reset'] = True
    return ret


def create_stats_app():
    routes = [('/', get_stats_dict, render_basic),
              POST('/reset', get_and_reset_stats_dict, render_basic)]
    app = Application(routes)
    return app
