from __future__ import unicode_literals

import inspect

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect

def get_arg_names(func):
    args, varargs, kw, defaults = inspect.getargspec(func)
    for a in args:
        if not isinstance(a, basestring):
            raise TypeError('does not support anonymous tuple arguments')
    return args

# "plugins" -> "resources" ?
class WorklesBase(object):
    def __init__(self, routes=None, plugins=None, render_factory=None):
        self.routes = []
        self.endpoint_args = {}
        for r in routes:
            # allow passing in a Map()
            nr = r.empty()
            if hasattr(nr, 'bind_render'):
                nr.bind_render(render_factory)
            self.routes.append(nr)
            self.endpoint_args[nr.endpoint] = get_arg_names(nr.endpoint)

        self.plugins = dict(plugins)

        self.render_factory = render_factory
        self.url_map = self.make_url_map()

    def make_url_map(self):
        ret = Map()  # support for options?
        for rule in self.routes:
            r = rule.empty()
            ret.add(r)
            endpoint_args = set(self.endpoint_args[r.endpoint])
            url_args = r.arguments
            app_args = self.injectable_names
            common_args = url_args & app_args
            if common_args:
                raise ValueError('Route args conflict with app args: ' + \
                                 repr(common_args) + ' (' + r.rule + ')')
            available_args = url_args | app_args
            unresolved_args = endpoint_args - available_args
            if unresolved_args:
                raise ValueError('Route endpoint has unresolved args: ' + \
                                 repr(unresolved_args)+' ('+ r.rule +')')
        return ret

    @property
    def injectable_names(self):
        return set(self.plugins.keys() + ['request', 'app'])

    def get_rules(self, r_map):
        for rf in self.routes:
            for rule in rf.get_rules(r_map):
                rule = rule.empty()
                yield rule

    def match(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        route, values = adapter.match(return_rule=True)
        request.path_params = values
        injectables = dict(self.plugins)
        injectables['request'] = request
        injectables['app'] = self
        injectables.update(values)
        ep_arg_names = self.endpoint_args[route.endpoint]
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
        elif callable(route.__dict__.get('render')):
            return route.render(ep_res)
        else:
            return HTTPException('no renderer registered for ' + repr(route) + \
                                 ' and no Response returned')
        #TODO: default renderer?

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.respond(request)
        return response(environ, start_response)


class Route(Rule):
    def __init__(self, rule_str, endpoint, render_arg=None, *a, **kw):
        super(Route, self).__init__(rule_str, *a, endpoint=endpoint, **kw)

        self.render = None
        self.render_arg = render_arg
        if callable(render_arg):
            self.render = render_arg

    def empty(self, keep_render=True):
        ret = Route(self.rule, self.endpoint, self.render_arg)
        ret.__dict__.update(super(Route, self).empty().__dict__)
        if keep_render:
            ret.render = self.render
        return ret

    def bind_render(self, render_factory):
        if self.render_arg is not None:
            self.render = render_factory(self.render_arg)
