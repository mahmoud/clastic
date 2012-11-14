from __future__ import unicode_literals

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect

class PluginDict(dict):
    pass

class WorklesBase(object):
    def __init__(self, routes=None, plugins=None, default_renderer=None):
        self.routes = routes  # allow passing in a Map()

        self.plugins = PluginDict(plugins)
        self.plugins.__dict__.update(self.plugins)

        self.default_renderer = default_renderer

        self.url_map = self.make_url_map()

    def make_url_map(self):
        ret = Map()  # support for options?
        for r in self.routes:
            ret.add(r.empty())
        return ret

    def add_route(self, route):
        #TODO
        raise NotImplemented

    #def add_renderer(self, key, render_func, is_default=False):
    #    self.renderers[key] = render_func
    #    if is_default:
    #        self.default_renderer = render_func

    def __call__(self, environ, start_response):
        request = Request(environ)
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            route, values = adapter.match(return_rule=True)
            ep_res = route.endpoint(self, request, **values)
        except (HTTPException, NotFound) as e:
            return e

        if isinstance(ep_res, Response):
            return ep_res(environ, start_response)

        if hasattr(route, 'renderer'):
            if callable(route.renderer):
                return route.renderer(ep_res)(environ, start_response)
            else:
                # TODO
                try:
                    renderer = self.renderers[ep.renderer]
                except KeyError, TypeError:
                    return HttpException('No renderer found for '+repr(ep.renderer))
        elif self.default_renderer:
            return self.default_renderer(ep_res)(environ, start_response)
        print 'passthru', repr(ep_res)
        return ep_res

class Route(Rule):
    def __init__(self, rule_str, endpoint, renderer, *a, **kw):
        super(Route, self).__init__(rule_str, *a, endpoint=endpoint, **kw)
        self.renderer = renderer

    def empty(self):
        ret = super(Route, self).empty()
        ret.renderer = self.renderer  # ret.__dict__.update(self.__dict__)?
        return ret

def default_response():
    pass
