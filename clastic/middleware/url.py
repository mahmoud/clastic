# -*- coding: utf-8 -*-

import sys
if sys.version_info < (3,3,):
    from collections import Mapping, Iterable
else:
    from collections.abc import Mapping, Iterable

from boltons.iterutils import is_iterable

try:
    unicode
except NameError:
    # py3
    unicode = str

from .core import Middleware


class ScriptRootMiddleware(Middleware):
    def __init__(self, provided_name='script_root'):
        self.provided_name = provided_name
        self.provides = (provided_name,)

    def request(self, next, request):
        return next(**{self.provided_name: request.script_root})


class GetParamMiddleware(Middleware):
    def __init__(self, params=None):
        # TODO: defaults?
        if isinstance(params, Mapping):
            self.params = params
        elif isinstance(params, unicode):
            self.params = {params: unicode}
        elif is_iterable(params):
            self.params = dict([(p, unicode) for p in params])
        else:
            raise TypeError('expected a string, dict, mapping, or iterable.')
        if not all([isinstance(v, type) for v in self.params.values()]):
            raise TypeError('param mapping values must be a valid type')
        self.provides = tuple(self.params.keys())

    def request(self, next, request):
        kwargs = {}
        for p_name, p_type in self.params.items():
            kwargs[p_name] = request.args.get(p_name, None, p_type)
        return next(**kwargs)

    def __repr__(self):
        cn = self.__class__.__name__
        param_map = dict([(n, t.__name__) for n, t in self.params.items()])
        return '%s(params=%r)' % (cn, param_map)
