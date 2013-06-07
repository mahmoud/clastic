from __future__ import unicode_literals

import os
if os.name != 'posix':
    # TODO: test on windows
    raise ImportError('webtop only supports posix platforms')

import clastic
from clastic import Application, StaticApplication
from clastic.render import json_response, AshesRenderFactory

_CLASTIC_PATH = os.path.dirname(os.path.abspath(clastic.__file__))
_ASSET_PATH = os.path.join(_CLASTIC_PATH, '_clastic_assets')

import psutil
from datetime import timedelta

_SIZE_SYMBOLS = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
_SIZE_BOUNDS = [(1024 ** i, sym) for i, sym in enumerate(_SIZE_SYMBOLS)]
_SIZE_RANGES = zip(_SIZE_BOUNDS, _SIZE_BOUNDS[1:])


def bytes2human(nbytes, ndigits=0):
    """
    >>> bytes2human(128991)
    u'126K'
    >>> bytes2human(100001221)
    u'95M'
    >>> bytes2human(0, 2)
    u'0.00B'
    """
    abs_bytes = abs(nbytes)
    for (size, symbol), (next_size, next_symbol) in _SIZE_RANGES:
        if abs_bytes <= next_size:
            break
    hnbytes = float(nbytes) / size
    return '{hnbytes:.{ndigits}f}{symbol}'.format(hnbytes=hnbytes,
                                                  ndigits=ndigits,
                                                  symbol=symbol)


_TOP_ATTRS = ('pid', 'username', 'get_nice', 'get_memory_info',
              'get_memory_percent', 'get_cpu_percent',
              'get_cpu_times', 'name', 'status')


def format_cpu_time(seconds):
    # TIME+ column shows process CPU cumulative time and it
    # is expressed as: "mm:ss.ms"
    # TODO: does not appear to handle days. .total_seconds()?
    ctime = timedelta(seconds=seconds)
    return "%s:%s.%s" % (ctime.seconds // 60 % 60,
                         str((ctime.seconds % 60)).zfill(2),
                         str(ctime.microseconds)[:2])


def get_process_dicts():
    proc_dicts = []
    for p in psutil.process_iter():
        try:
            proc_dicts.append(p.as_dict(_TOP_ATTRS))
        except psutil.NoSuchProcess:
            pass

    # return processes sorted by CPU percent usage
    proc_dicts.sort(key=lambda x: x['cpu_percent'], reverse=True)
    return proc_dicts


def top():
    entries = [format_dict(pd) for pd in get_process_dicts()]
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
    ret['cpu'] = '' if pd['cpu_percent'] is None else pd['cpu_percent']
    ret['mem'] = ''
    if pd['memory_percent'] is not None:
        ret['mem'] = round(pd['memory_percent'], 1)
    ret['name'] = pd['name'] or ''
    return ret


def create_app():
    print _ASSET_PATH
    routes = [('/', top, 'top.html'),
              ('/clastic_assets/', StaticApplication(_ASSET_PATH)),
              ('/json/', top, json_response)]
    arf = AshesRenderFactory(os.path.dirname(__file__))
    app = Application(routes, {}, arf)
    return app

if __name__ == '__main__':
    create_app().serve()
