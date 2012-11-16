from __future__ import unicode_literals

import inspect
import collections

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect

from werkzeug.routing import parse_rule

RESERVED_ARGS = ['req', 'request', 'application']

def get_arg_names(func):
    args, varargs, kw, defaults = inspect.getargspec(func)
    for a in args:
        if not isinstance(a, basestring):
            raise TypeError('does not support anonymous tuple arguments')
    return args


# turn into combination Map/RuleFactory
class WorklesBase(Map):
    def __init__(self, routes=None, resources=None, render_factory=None,
                 middlewares=None, **map_kwargs):
        map_kwargs.pop('rules', None)
        super(WorklesBase, self).__init__(**map_kwargs)

        self.routes = []
        self.resources = dict(resources or {})
        self.middlewares = list(middlewares or [])
        self.render_factory = render_factory
        self.endpoint_args = {}
        self._map_kwargs = map_kwargs
        for entry in routes:
            rule_factory = Route.cast(entry)
            for r in rule_factory.get_rules(self):
                self.add_route(r)

    def add_route(self, route):
        # note: currently only works with individual routes
        nr = route.copy()  # is copy necessary here?
        self.add(nr)
        return nr

    @property
    def injectable_names(self):
        return set(self.resources.keys() + RESERVED_ARGS)

    def get_rules(self, r_map=None):
        if r_map is None:
            r_map = self
        for rf in self.routes:
            for rule in rf.get_rules(r_map):
                yield rule  # is yielding bound rules bad?

    def match(self, request):
        adapter = self.bind_to_environ(request.environ)
        route, values = adapter.match(return_rule=True)
        request.path_params = values
        injectables = dict(self.resources)
        injectables['request'] = request
        injectables['req'] = request
        injectables['application'] = self
        injectables.update(values)
        ep_arg_names = route.endpoint_args
        ep_kwargs = dict([(k, v) for k, v in injectables.items()
                          if k in ep_arg_names])
        return route, ep_kwargs

    def respond(self, request):
        try:
            route, ep_kwargs = self.match(request)
            ep_res = route.endpoint(**ep_kwargs)
        except (HTTPException, NotFound) as e:
            return e

        if isinstance(ep_res, Response):
            return ep_res
        elif callable(getattr(route, 'render', None)):
            return route.render(ep_res)
        else:
            import pdb;pdb.set_trace()
            return HTTPException('no renderer registered for ' + repr(route) + \
                                 ' and no Response returned')
        #TODO: default renderer?

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.respond(request)
        return response(environ, start_response)


class Middleware(object):
    unique = True
    reorderable = True
    provides = ()

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def overridable(self):
        # thought: list of overridable provides?
        return tuple(provides)

    def __eq__(self, other):
        return type(self) == type(other)

    def __ne__(self, other):
        return type(self) != type(other)

    request = None
    endpoint = None
    render = None


class DummyMiddleware(Middleware):
    def __init__(self):
        pass

    def request(self, next, request):
        print self, 'handling', id(request)
        try:
            ret = next()
        except:
            print self, 'uhoh'
            raise
        print self, 'hooray'
        return ret


def merge_middlewares(old, new):
    old = list(old)
    merged = list(new)
    for mw in old:
        if mw.unique and mw in merged:
            if mw.reorderable:
                continue
            else:
                raise ValueError('multiple inclusion of unique '
                                 'middleware '+mw.name)
        merged.append(mw)
    # todo: resolve provides conflicts
    return merged


class Route(Rule):
    def __init__(self, rule_str, endpoint, render_arg=None, *a, **kw):
        super(Route, self).__init__(rule_str, *a, endpoint=endpoint, **kw)
        self._middlewares = []
        self._resources = {}
        self.endpoint_args = get_arg_names(endpoint)

        self._render = None
        self.render_arg = render_arg
        if callable(render_arg):
            self._render = render_arg

    @property
    def is_bound(self):
        return self.map is not None

    @property
    def render(self):
        return self._render

    def empty(self):
        ret = Route(self.rule, self.endpoint, self.render_arg)
        ret.__dict__.update(super(Route, self).empty().__dict__)
        return ret

    def copy(self):
        # todo: there's probably more
        ret = self.empty()
        ret._render = self.render
        ret._middlewares = list(self._middlewares)
        return ret

    def get_middlewares(self, new_middlewares=None):
        if new_middlewares:
            return merge_middlewares(self._middlewares, new_middlewares)
        else:
            return self._middlewares

    def bind(self, app):
        resources = app.__dict__.get('resources', {})
        render_factory = app.__dict__.get('render_factory')
        middlewares = app.__dict__.get('middlewares', [])

        merged_resources = self._resources.copy()
        merged_resources.update(resources)
        merged_mw = self.get_middlewares(middlewares)

        r_copy = self.copy()
        try:
            r_copy._bind_args(app, merged_resources, merged_mw)
        except:
            raise

        self._bind_args(app, merged_resources, middlewares)
        self.bind_render(render_factory)
        return self

    def _bind_args(self, url_map, resources, middlewares):
        super(Route, self).bind(url_map, rebind=True)
        url_args = self.arguments
        endpoint_args = set(self.endpoint_args)
        mw_args = set().union(*[set(mw.provides) for mw in middlewares])
        app_args = set(resources.keys()) | set(mw_args) | set(RESERVED_ARGS)
        common_args = url_args & app_args
        if common_args:
            raise ValueError('Route args conflict with app args: ' + \
                             repr(common_args) + ' (' + self.rule + ')')
        available_args = url_args | app_args
        unresolved_args = endpoint_args - available_args
        if unresolved_args:
            import pdb;pdb.set_trace()
            raise ValueError('Route endpoint has unresolved args: ' + \
                             repr(unresolved_args)+' ('+ self.rule +')')

    def bind_render(self, render_factory):
        # control over whether or not to override?
        if callable(render_factory) and self.render_arg is not None:
            self._render = render_factory(self.render_arg)

    @classmethod
    def cast(cls, in_arg):
        if isinstance(in_arg, cls):
            return in_arg
        elif isinstance(in_arg, Rule):
            ret = cls(in_arg.rule, in_arg.endpoint)
            ret.__dict__.update(in_arg.empty().__dict__)
            return ret
        elif isinstance(in_arg, collections.Sequence):
            try:
                return cls(*in_arg)
            except TypeError:
                pass
        raise TypeError('incompatible Route type: ' + repr(in_arg))
