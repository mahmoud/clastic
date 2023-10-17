
import os

from operator import itemgetter
from datetime import timedelta

from boltons.strutils import bytes2human
psutil = None

import clastic
from clastic import Application, StaticApplication, META_ASSETS_APP
from clastic.render import render_json, AshesRenderFactory

_CUR_PATH = os.path.dirname(__file__)


_TOP_ATTRS = ('pid', 'username', 'nice', 'memory_info',
              'memory_percent', 'cpu_percent',
              'cpu_times', 'name', 'status')


def format_cpu_time(seconds):
    # TIME+ column shows process CPU cumulative time and it
    # is expressed as: "mm:ss.ms"
    # TODO: does not appear to handle days. .total_seconds()?
    ctime = timedelta(seconds=seconds)
    return "%s:%s.%s" % (ctime.seconds // 60 % 60,
                         str((ctime.seconds % 60)).zfill(2),
                         str(ctime.microseconds)[:2])


def get_process_dicts():
    ret = []
    for p in psutil.process_iter():
        try:
            ret.append(p.as_dict(_TOP_ATTRS))
        except psutil.NoSuchProcess:
            pass
    return ret


def top(sort_key='cpu'):
    global psutil
    try:
        import psutil
    except ImportError as ie:
        error_msg = ('Clastic webtop requires psutil to function.'
                     ' pip install psutil to access this page. (got: %r)'
                     % (ie,))
        return {'entries': [],
                'error': error_msg}

    # TODO: add sort key middleware
    _key = itemgetter(sort_key)
    entries = [format_dict(pd) for pd in get_process_dicts()]

    # handle an apparent bug in psutil where the first call of the
    # process does not return any cpu percentages. sorting by memory
    # percentages instead.
    try:
        sort_total = sum([_key(x) for x in entries if _key(x) is not None])
        if not sort_total:
            sort_key = 'mem'
            _key = itemgetter(sort_key)
    except TypeError:
        pass
    entries.sort(key=_key, reverse=True)
    return {'entries': entries}


def format_dict(pd):
    ret = {}
    ret['pid'] = pd['pid']
    ret['time'] = ''
    if pd['cpu_times'] is not None:
        ret['time'] = format_cpu_time(sum(pd['cpu_times']))
    ret['user'] = pd['username'][:12]
    ret['ni'] = pd['nice']

    mem_info = pd['memory_info']
    ret['virt'] = bytes2human(getattr(mem_info, 'vms', 0))
    ret['res'] = bytes2human(getattr(mem_info, 'rss', 0))
    ret['cpu'] = -0.0 if pd['cpu_percent'] is None else pd['cpu_percent']
    ret['mem'] = -0.0
    if pd['memory_percent'] is not None:
        ret['mem'] = round(pd['memory_percent'], 1)
    ret['name'] = pd['name'] or ''
    return ret


def create_app():
    routes = [('/', top, 'top.html'),
              ('/clastic_assets/', META_ASSETS_APP),
              ('/json/', top, render_json)]
    arf = AshesRenderFactory(_CUR_PATH)
    app = Application(routes, render_factory=arf)
    return app


if __name__ == '__main__':
    create_app().serve()
