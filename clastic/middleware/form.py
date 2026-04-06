# -*- coding: utf-8 -*-

from collections.abc import Mapping, Iterable

from boltons.iterutils import is_iterable


from .core import Middleware


class PostDataMiddleware(Middleware):
    def __init__(self, params=None):
        # TODO: defaults?
        if isinstance(params, Mapping):
            self.params = params
        elif isinstance(params, str):
            self.params = {params: str}
        elif is_iterable(params):
            self.params = dict([(p, str) for p in params])
        else:
            raise TypeError('expected a string, dict, mapping, or iterable.')
        if not all([isinstance(v, type) for v in self.params.values()]):
            raise TypeError('param mapping values must be a valid type')
        self.provides = tuple(self.params.keys())

    def request(self, next, request):
        kwargs = {}
        for p_name, p_type in self.params.items():
            kwargs[p_name] = request.form.get(p_name, None, p_type)
        return next(**kwargs)

    def __repr__(self):
        cn = self.__class__.__name__
        param_map = dict([(n, t.__name__) for n, t in self.params.items()])
        return '%s(params=%r)' % (cn, param_map)
