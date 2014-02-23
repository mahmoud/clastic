# -*- coding: utf-8 -*-

from collections import Mapping, Iterable

from .core import Middleware


class PostDataMiddleware(Middleware):
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
            kwargs[p_name] = request.form.get(p_name, None, p_type)
        return next(**kwargs)

    def __repr__(self):
        cn = self.__class__.__name__
        param_map = dict([(n, t.__name__) for n, t in self.params.items()])
        return '%s(params=%r)' % (cn, param_map)
