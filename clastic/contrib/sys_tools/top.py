from __future__ import unicode_literals

from clastic import Application
from clastic.render import json_response, AshesRenderFactory

import os
import sys
if os.name != 'posix':
    raise ImportError('webtop only supports posix platforms')
import psutil
from datetime import timedelta


def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = int(float(n) / prefix[s])
            return '%s%s' % (value, s)
    return "%sB" % n


def poll():
    procs = []
    procs_status = {}
    for p in psutil.process_iter():
        try:
            p.dict = p.as_dict(['username', 'get_nice', 'get_memory_info',
                                'get_memory_percent', 'get_cpu_percent',
                                'get_cpu_times', 'name', 'status'])
            try:
                procs_status[str(p.dict['status'])] += 1
            except KeyError:
                procs_status[str(p.dict['status'])] = 1
        except psutil.NoSuchProcess:
            pass
        else:
            procs.append(p)

    # return processes sorted by CPU percent usage
    processes = sorted(procs,
                       key=lambda p: p.dict['cpu_percent'], reverse=True)
    return (processes, procs_status)


def top():
    return {'lines': top_structured(*poll())}


def top_structured(procs, procs_status):
    top = []
    for p in procs:
        # TIME+ column shows process CPU cumulative time and it
        # is expressed as: "mm:ss.ms"
        if p.dict['cpu_times'] != None:
            ctime = timedelta(seconds=sum(p.dict['cpu_times']))
            ctime = "%s:%s.%s" % (ctime.seconds // 60 % 60,
                                  str((ctime.seconds % 60)).zfill(2),
                                  str(ctime.microseconds)[:2])
        else:
            ctime = ''
        if p.dict['memory_percent'] is not None:
            p.dict['memory_percent'] = round(p.dict['memory_percent'], 1)
        else:
            p.dict['memory_percent'] = ''
        if p.dict['cpu_percent'] is None:
            p.dict['cpu_percent'] = ''
        line = {'pid': p.pid,
                'user': p.dict['username'][:8],
                'ni': p.dict['nice'],
                'virt': bytes2human(getattr(p.dict['memory_info'], 'vms', 0)),
                'res': bytes2human(getattr(p.dict['memory_info'], 'rss', 0)),
                'cpu': p.dict['cpu_percent'],
                'mem': p.dict['memory_percent'],
                'time': ctime,
                'name': p.dict['name'] or '',
                }
        top.append(line)
    return top


def create_app():
    routes = [('/', top, 'top.html'),
              ('/json/', top, json_response)]
    arf = AshesRenderFactory(os.path.dirname(__file__))
    app = Application(routes, None, arf)
    return app

if __name__ == '__main__':
    create_app().serve()
