# -*- coding: utf-8 -*-

import cProfile
from pstats import Stats

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from .core import Middleware


_prof_tmpl = '<html><body><pre>%s</pre></body</html>'
_sort_keys = {'cumulative': 'cumulative time, i.e., includes time in called functions.',
              'file': 'source file',
              'line': 'line number',
              'name': 'function name',
              'module': 'source module',
              'nfl': 'name/file/line',
              'pcalls': 'primitive (non-recursive) calls',
              'stdname': 'standard name (includes path)',
              'time': 'internal time, i.e., time in this function scope'}


class SimpleProfileMiddleware(Middleware):
    def __init__(self, sort_param_name='_prof_sort', get_param_name='_prof', raise_exc=True):
        self.get_param_name = get_param_name
        self.sort_param_name = sort_param_name
        self.raise_exc = raise_exc

    def request(self, next, request):
        if not request.args.get(self.get_param_name):
            return next()
        sort_param = request.args.get(self.sort_param_name, 'time')
        if sort_param not in _sort_keys:
            raise KeyError('%s is not a supported sort_key. choose from: %r'
                           % (sort_param, _sort_keys))
        profiler = cProfile.Profile()
        try:
            ret = profiler.runcall(next)
        except Exception:
            if self.raise_exc:
                raise

        buff = StringIO()
        Stats(profiler, stream=buff).sort_stats(sort_param).print_stats()
        body = _prof_tmpl % buff.getvalue()
        ret.set_data(body)

        return ret
