from __future__ import unicode_literals

from collections import defaultdict, Sequence
from werkzeug.wrappers import Request
from werkzeug.routing import Map, Rule, RuleFactory
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.utils import cached_property

from sinter import get_arg_names, inject, make_middleware_chain

# TODO: check resources for conflicts with reserved args
# TODO: check for URL pattern conflicts?

RESERVED_ARGS = ('request', 'next', 'context', '_application',
                 '_route', '_endpoint')

class Application(Map):
    def __init__(self, routes=None, resources=None, render_factory=None,
                 middlewares=None, **map_kwargs):
        map_kwargs.pop('rules', None)
        super(Application, self).__init__(**map_kwargs)

        routes = routes or []
        self.routes = []
        self.resources = dict(resources or {})
        resource_conflicts = [r for r in RESERVED_ARGS if r in self.resources]
        if resource_conflicts:
            raise NameError('resource names conflict with builtins: %r',
                            resource_conflicts)
        self.middlewares = list(middlewares or [])
        check_middlewares(self.middlewares)
        self.render_factory = render_factory
        self.endpoint_args = {}
        self._map_kwargs = map_kwargs
        for entry in routes:
            self.add(entry)

    def add(self, entry, rebind_render=True):
        rf = cast_to_rule_factory(entry)
        rebind_render = getattr(rf, 'rebind_render', rebind_render)
        for route in rf.get_rules(self):
            route.bind(self, rebind_render)
            self.routes.append(route)
            self._rules.append(route)
            self._rules_by_endpoint.setdefault(route.endpoint, []).append(route)
        self._remap = True

    def get_rules(self, r_map=None):
        r_map = self
        for rf in self.routes:
            for rule in rf.get_rules(r_map):
                yield rule  # is yielding bound rules bad?

    def match(self, request):
        adapter = self.bind_to_environ(request.environ)
        route, url_args = adapter.match(return_rule=True)
        request.path_params = url_args
        injectables = dict(self.resources)
        injectables['request'] = request
        injectables['_application'] = self
        injectables.update(url_args)
        ep_arg_names = route.endpoint_args
        ep_kwargs = dict([(k, v) for k, v in injectables.items()
                          if k in ep_arg_names])
        return route, ep_kwargs

    def respond(self, request):
        try:
            route, ep_kwargs = self.match(request)
            ep_kwargs['request'] = request
            ep_res = route.execute(**ep_kwargs)
        except (HTTPException, NotFound) as e:
            return e
        return ep_res

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.respond(request)
        return response(environ, start_response)


class SubApplication(RuleFactory):
    def __init__(self, prefix, app, rebind_render=False):
        self.prefix = prefix.rstrip('/')
        self.app = app
        self.rebind_render = rebind_render

    def get_rules(self, url_map):
        for rules in self.app.get_rules(url_map):
            for rule in rules.get_rules(url_map):
                yld = rule.empty()
                yld.rule = self.prefix + yld.rule
                yield yld


class Route(Rule):
    def __init__(self, rule_str, endpoint, render_arg=None, *a, **kw):
        super(Route, self).__init__(rule_str, *a, endpoint=endpoint, **kw)
        self._middlewares = []
        self._resources = {}
        self._bound_apps = []
        self.endpoint_args = get_arg_names(endpoint)
        self.endpoint_reqs = get_arg_names(endpoint, True)

        self._execute = None
        self._render = None
        self._render_factory = None
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
        ret._middlewares = tuple(self._middlewares)
        ret._resources = dict(self._resources)
        ret._bound_apps = tuple(self._bound_apps)
        ret._render_factory = self._render_factory
        ret._render = self._render
        ret._execute = self._execute
        return ret

    def bind(self, app, rebind_render=True):
        resources = app.__dict__.get('resources', {})
        middlewares = app.__dict__.get('middlewares', [])
        if rebind_render:
            render_factory = app.__dict__.get('render_factory')
        else:
            render_factory = self._render_factory

        merged_resources = dict(self._resources)
        merged_resources.update(resources)
        merged_mw = merge_middlewares(self._middlewares, middlewares)
        r_copy = self.empty()
        try:
            r_copy._bind_args(app, merged_resources, merged_mw, render_factory)
        except:
            raise

        self._bind_args(app, merged_resources, merged_mw, render_factory)
        self._bound_apps += (app,)
        return self

    def _bind_args(self, url_map, resources, middlewares, render_factory):
        super(Route, self).bind(url_map, rebind=True)
        url_args = set(self.arguments)
        builtin_args = set(RESERVED_ARGS)
        resource_args = set(resources.keys())

        tmp_avail_args = {'url': url_args,
                          'builtins': builtin_args,
                          'resources': resource_args}
        check_middlewares(middlewares, tmp_avail_args)
        provided = resource_args | builtin_args | url_args
        if callable(render_factory) and self.render_arg is not None:
            _render = render_factory(self.render_arg)
        else:
            _render = lambda context: context
        _execute = make_middleware_chain(middlewares, self.endpoint, _render, provided)

        self._resources.update(resources)
        self._middlewares = middlewares
        self._render_factory = render_factory
        self._render = _render
        self._execute = _execute

    def execute(self, request, **kwargs):
        injectables = {'request': request,
                       '_application': self._bound_apps[-1],
                       '_endpoint': self.endpoint,
                       '_route': self}
        injectables.update(self._resources)
        injectables.update(kwargs)
        return inject(self._execute, injectables)


# exec req middlewares
# -> exec endpoint middlewares
#  -> endpoint (*get context or response)
# -> ret endpoint middlewares
# -> exec render middlewares (if not response)
#  -> render (*get response)
# -> ret render middlewares
# ret req middlewares


class Middleware(object):
    unique = True
    reorderable = True
    provides = ()
    endpoint_provides = ()
    render_provides = ()

    request = None
    endpoint = None
    render = None

    @property
    def name(self):
        return self.__class__.__name__

    def __eq__(self, other):
        return type(self) == type(other)

    def __ne__(self, other):
        return type(self) != type(other)

    @cached_property
    def requirements(self):
        reqs = []
        for func_name in ('request', 'endpoint', 'render'):
            func = getattr(self, func_name, None)
            if func:
                reqs.extend(get_arg_names(func, True))
        return set(reqs)

    @cached_property
    def arguments(self):
        args = []
        for func_name in ('request', 'endpoint', 'render'):
            func = getattr(self, func_name, None)
            if func:
                args.extend(get_arg_names(func))
        return set(args)


def check_middleware(mw):
    for f_name in ('request', 'endpoint', 'render'):
        func = getattr(mw, f_name, None)
        if not func:
            continue
        if not callable(func):
            raise TypeError('expected middleware.'+f_name+' to be a function')
        if not get_arg_names(func)[0] == 'next':
            raise TypeError("middleware functions must take a first parameter 'next'")


def check_middlewares(middlewares, args_dict=None):
    args_dict = args_dict or {}

    provided_by = defaultdict(list)
    for source, arg_list in args_dict.items():
        for arg_name in arg_list:
            provided_by[arg_name].append(source)

    for mw in middlewares:
        check_middleware(mw)
        for arg in mw.provides:
            provided_by[arg].append(mw)

    conflicts = [(n, tuple(ps)) for (n, ps) in provided_by.items() if len(ps) > 1]
    if conflicts:
        raise NameError('found conflicting provides: '+repr(conflicts))
    return True


def merge_middlewares(old, new):
    # TODO: since duplicate provides aren't allowed
    # an error needs to be raised if a middleware is
    # set to non-unique and has provides params
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
    return merged


class DummyMiddleware(Middleware):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def request(self, next, request):
        type_name = self.__class__.__name__
        if self.verbose:
            print type_name, '- handling', id(request)
        try:
            ret = next()
        except Exception as e:
            if self.verbose:
                print type_name, '- uhoh:', repr(e)
            raise
        if self.verbose:
            print type_name, '- hooray:', repr(ret)
        return ret


def cast_to_rule_factory(in_arg):
    if isinstance(in_arg, Route):
        return in_arg
    elif isinstance(in_arg, Rule):
        ret = Route(in_arg.rule, in_arg.endpoint)
        ret.__dict__.update(in_arg.empty().__dict__)
        return ret
    elif isinstance(in_arg, Sequence):
        try:
            if isinstance(in_arg[1], Application):
                return SubApplication(*in_arg)
            if callable(in_arg[1]):
                return Route(*in_arg)
        except TypeError:
            pass
    if isinstance(in_arg, RuleFactory):
        return in_arg
    raise TypeError('Could not create routes from ' + repr(in_arg))
