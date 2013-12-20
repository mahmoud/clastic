# -*- coding: utf-8 -*-

from collections import Mapping, Iterable

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
        elif isinstance(params, basestring):
            self.params = {params: unicode}
        elif isinstance(params, Iterable):
            self.params = dict([(p, unicode) for p in params])
        else:
            raise TypeError('expected a string, dict, mapping, or iterable.')
        if not all([isinstance(v, type) for v in self.params.values()]):
            raise TypeError('param mapping values must be a valid type')
        self.provides = tuple(self.params.iterkeys())

    def request(self, next, request):
        kwargs = {}
        for p_name, p_type in self.params.items():
            kwargs[p_name] = request.args.get(p_name, None, p_type)
        return next(**kwargs)

    def __repr__(self):
        cn = self.__class__.__name__
        param_map = dict([(n, t.__name__) for n, t in self.params.items()])
        return '%s(params=%r)' % (cn, param_map)
