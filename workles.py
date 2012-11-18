from __future__ import unicode_literals

import inspect
import collections
from collections import defaultdict
import types

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect, cached_property

from werkzeug.routing import parse_rule

# TODO: 'next' is really only reserved for middlewares
RESERVED_ARGS = ['req', 'request', 'application', 'matched_route', 'matched_endpoint', 'next']

def get_arg_names(f, only_required=False):
    arg_names, _, _, defaults = inspect.getargspec(f)
    if not all([isinstance(a, basestring) for a in arg_names]):
        raise TypeError('does not support anonymous tuple arguments '
                        'or any other strange args for that matter.')
    ret = list(arg_names)
    if isinstance(f, types.MethodType):
        ret = ret[1:]  # throw away "self"

    if only_required and defaults:
        ret = ret[:-len(defaults)]

    return ret


def inject(f, injectables):
    arg_names, _, _, defaults = inspect.getargspec(f)
    if defaults:
        defaults = dict(reversed(zip(reversed(arg_names), reversed(defaults))))
    else:
        defaults = {}
    if isinstance(f, types.MethodType):
        arg_names = arg_names[1:] #throw away "self"
    args = {}
    for n in arg_names:
        if n in injectables:
            args[n] = injectables[n]
        else:
            args[n] = defaults[n]
    return f(**args)


class Application(Map):
    def __init__(self, routes=None, resources=None, render_factory=None,
                 middlewares=None, **map_kwargs):
        map_kwargs.pop('rules', None)
        super(Application, self).__init__(**map_kwargs)

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

    request = None
    endpoint = None
    render = None

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def overridable(self):
        # thought: list of overridable provides?
        return tuple(self.provides)

    def __eq__(self, other):
        return type(self) == type(other)

    def __ne__(self, other):
        return type(self) != type(other)

    @cached_property
    def requirements(self):
        reqs = []
        if self.request:
            reqs.extend(get_arg_names(self.request, True))
        if self.endpoint:
            reqs.extend(get_arg_names(self.endpoint, True))
        if self.render:
            reqs.extend(get_arg_names(self.render, True))
        return set(reqs)

    @cached_property
    def arguments(self):
        args = []
        if self.request:
            args.extend(get_arg_names(self.request))
        if self.endpoint:
            args.extend(get_arg_names(self.endpoint))
        if self.render:
            args.extend(get_arg_names(self.render))
        return set(args)


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
        self._reqs = None  # TODO
        self._args = None
        self._bound_apps = []
        self.endpoint_args = get_arg_names(endpoint)
        self.endpoint_reqs = get_arg_names(endpoint, True)

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
        self._bound_apps.append(app)
        return self

    def _bind_args(self, url_map, resources, middlewares):
        super(Route, self).bind(url_map, rebind=True)
        url_args = set(self.arguments)
        builtin_args = set(RESERVED_ARGS)
        resource_args = set(resources.keys() + self._resources.keys())

        endpoint_args = set(self.endpoint_args)
        endpoint_reqs = set(self.endpoint_reqs)
        spec_mw = self.get_middlewares(middlewares)

        provided_by = defaultdict(list)
        for arg in builtin_args:
            provided_by[arg].append('builtins')
        for arg in url_args:
            provided_by[arg].append('url')
        for arg in resource_args:
            provided_by[arg].append('resources')
        for mw in spec_mw:
            for arg in mw.provides:
                provided_by[arg].append(mw)

        conflicts = [(n, tuple(ps)) for (n, ps) in provided_by.items() if len(ps) > 1]
        if conflicts:
            raise ValueError('route argument conflicts: '+repr(conflicts))

        route_reqs = set(endpoint_reqs)
        route_args = set(endpoint_args)
        provided = resource_args | builtin_args | url_args
        mw_unresolved = defaultdict(list)
        for mw in spec_mw:
            route_reqs.update(mw.requirements)
            route_args.update(mw.arguments)
            cur_unresolved = mw.requirements - provided
            if cur_unresolved:
                mw_unresolved[mw] = tuple(cur_unresolved)
            provided.update(set(mw.provides))
        if mw_unresolved:
            raise ValueError('unresolved middleware arguments: '+repr(dict(mw_unresolved)))

        ep_unresolved = endpoint_reqs - provided
        if ep_unresolved:
            raise ValueError('unresolved endpoint arguments: '+repr(tuple(ep_unresolved)))

        self._resources.update(resources)
        self._middlewares = spec_mw
        self._reqs = route_reqs
        self._args = route_args

    def execute(request):  # , resources=None):
        injectables = {'req': request,
                       'request': request,
                       'application': self._bound_apps[-1],
                       'matched_endpoint': self.endpoint,
                       'matched_route': self.route}
        injectables.update(self._resources)

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
        elif isinstance(in_arg, Application):
            pass
        raise TypeError('incompatible Route type: ' + repr(in_arg))


# GET/POST param middleware factory
# ordered sets?

# should resource values be bound into the route,
# or just check argument names and let the application do the
# resource merging?
