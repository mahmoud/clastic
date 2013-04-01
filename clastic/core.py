from __future__ import unicode_literals

import os
from collections import Sequence
from argparse import ArgumentParser
from werkzeug.wrappers import Request
from werkzeug.routing import Map, Rule, RuleFactory
from werkzeug.exceptions import HTTPException, NotFound
from server import run_simple

from sinter import inject, get_arg_names, getargspec
from middleware import (check_middlewares,
                        merge_middlewares,
                        make_middleware_chain)

# TODO: check for URL pattern conflicts?

RESERVED_ARGS = ('request', 'next', 'context', '_application',
                 '_route', '_endpoint')


class Application(Map):
    def __init__(self, routes=None, resources=None, render_factory=None,
                 middlewares=None, error_handlers=None, **map_kwargs):
        map_kwargs.pop('rules', None)
        super(Application, self).__init__(**map_kwargs)

        routes = routes or []
        self.error_handlers = dict(error_handlers or {})
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
            # some versions of 2.6 die on unicode kwarg names
            ep_kwargs = dict([(str(k), v) for k, v in ep_kwargs.items()])
            ep_res = route.execute(**ep_kwargs)
        except Exception as e:
            code = getattr(e, 'code', None)
            if code in self.error_handlers:
                handler = self.error_handlers[code]
            else:
                handler = self.error_handlers.get(None)

            if handler:
                injectables = {'error': e,
                               'request': request,
                               '_application': self}
                return inject(handler, injectables)
            else:
                if code and callable(getattr(e, 'get_response', None)):
                    return e.get_response(request)
                else:
                    raise

        return ep_res

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.respond(request)
        return response(environ, start_response)

    def serve(self,
              address='0.0.0.0',
              port=5000,
              use_meta=True,
              use_lint=True,
              use_reloader=True,
              use_debugger=True,
              use_static=True,
              static_prefix='static',
              static_path=None, **kw):
        parser = create_dev_server_parser()
        args, _ = parser.parse_known_args()

        address = args.address or address
        port = args.port if args.port is not None else port
        kw['use_reloader'] = args.use_reloader and use_reloader
        kw['use_debugger'] = args.use_debugger and use_debugger
        # kw['processes'] = args.processes or processes
        use_meta = args.use_meta and use_meta
        use_lint = args.use_lint and use_lint
        use_static = args.use_static and use_static

        wrapped_wsgi = self
        if use_meta:
            from meta import MetaApplication
            self.add(('/_meta/', MetaApplication))
        if use_static:
            from werkzeug.wsgi import SharedDataMiddleware
            static_path = args.static_path or static_path or \
                os.path.join(os.getcwd(), 'static')
            static_prefix = args.static_prefix or static_prefix
            static_prefix = '/' + unicode(static_prefix).lstrip('/')
            paths = {static_prefix: static_path}
            wrapped_wsgi = SharedDataMiddleware(wrapped_wsgi, paths)
        if use_lint:
            from werkzeug.contrib.lint import LintMiddleware
            wrapped_wsgi = LintMiddleware(wrapped_wsgi)
        # some versions of 2.6 die on unicode dictionary keys
        kw = dict([(str(k), v) for k, v in kw.items()])

        if kw.get('_jk_just_testing'):
            return True
        run_simple(address, port, wrapped_wsgi, **kw)


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

        self._execute = None
        self._render = None
        self._render_factory = None
        self.render_arg = render_arg
        if callable(render_arg):
            self._render = render_arg

    def get_info(self):
        ret = {}
        route = self
        ep_args, _, _, ep_defaults = getargspec(route.endpoint)
        ep_defaults = dict(reversed(zip(reversed(ep_args),
                                        reversed(ep_defaults or []))))
        ret['url_rule'] = route.rule
        ret['endpoint'] = route.endpoint
        ret['endpoint_args'] = ep_args
        ret['endpoint_defaults'] = ep_defaults
        ret['render_arg'] = route.render_arg
        srcs = {}
        for arg in route.endpoint_args:
            if arg in RESERVED_ARGS:
                srcs[arg] = 'builtin'
            elif arg in route.arguments:
                srcs[arg] = 'url'
            elif arg in ep_defaults:
                srcs[arg] = 'default'
            for mw in route._middlewares:
                if arg in mw.provides:
                    srcs[arg] = mw
            if arg in route._resources:
                srcs[arg] = 'resources'
            # TODO: trace to application if middleware/resource
        ret['sources'] = srcs
        return ret

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
        if callable(render_factory) and self.render_arg is not None \
                and not callable(self.render_arg):
            _render = render_factory(self.render_arg)
        elif callable(self._render):
            _render = self._render
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


def create_dev_server_parser():
    parser = ArgumentParser()
    parser.add_argument('--address')
    parser.add_argument('--port', type=int)
    parser.add_argument('--static-path')
    parser.add_argument('--static-prefix')
    parser.add_argument('--no-static', dest='use_static',
                        action='store_false')
    parser.add_argument('--no-meta', dest='use_meta',
                        action='store_false')
    parser.add_argument('--no-reloader', dest='use_reloader',
                        action='store_false')
    parser.add_argument('--no-debugger', dest='use_debugger',
                        action='store_false')
    parser.add_argument('--no-wsgi-lint', dest='use_lint',
                        action='store_false')
    parser.add_argument('--processes', type=int, help="number of"
                        " processes, if you want a forking server")
    return parser
