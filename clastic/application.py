# -*- coding: utf-8 -*-

import sys
from collections import Sequence

from werkzeug.wrappers import BaseResponse
from werkzeug.wrappers import Request, Response

from .routing import (BaseRoute,
                      Route,
                      NullRoute,
                      RESERVED_ARGS)
from .tbutils import TracebackInfo
from .middleware import check_middlewares
from ._errors import (NotFound,
                      MethodNotAllowed,
                      InternalServerError)

S_REDIRECT = 'redirect'
S_NORMALIZE = 'normalize'
S_STRICT = 'strict'


def cast_to_route_factory(in_arg):
    if isinstance(in_arg, BaseRoute):
        return in_arg
    elif isinstance(in_arg, Sequence):
        try:
            if isinstance(in_arg[1], BaseApplication):
                return SubApplication(*in_arg)
            if callable(in_arg[1]):
                return Route(*in_arg)
        except TypeError:
            pass
    raise TypeError('Could not create routes from %r' % in_arg)


class BaseApplication(object):
    request_type = Request
    response_type = Response

    def __init__(self, routes=None, resources=None, render_factory=None,
                 middlewares=None, **kwargs):
        self.debug = kwargs.pop('debug', None)
        if kwargs:
            raise TypeError('unexpected keyword args: %r' % kwargs.keys())
        self.resources = dict(resources or {})
        resource_conflicts = [r for r in RESERVED_ARGS if r in self.resources]
        if resource_conflicts:
            raise NameError('resource names conflict with builtins: %r' %
                            resource_conflicts)
        self.middlewares = list(middlewares or [])
        check_middlewares(self.middlewares)
        self.render_factory = render_factory

        routes = routes or []
        self.routes = []
        self._null_route = NullRoute()
        self._null_route.bind(self)
        for entry in routes:
            self.add(entry)

    def add(self, entry, index=None, rebind_render=True):
        if index is None:
            index = len(self.routes)
        rf = cast_to_route_factory(entry)
        rebind_render = getattr(rf, 'rebind_render', rebind_render)
        for route in rf.iter_routes(self):
            route.bind(self, rebind_render)
            self.routes.insert(index, route)
            index += 1

    def __call__(self, environ, start_response):
        request = self.request_type(environ)
        response = self.dispatch(request)
        return response(environ, start_response)

    def dispatch(self, request, slashes=S_NORMALIZE):
        url_path = request.path
        method = request.method

        _excs = []
        allowed_methods = set()
        for route in self.routes:
            params = route.match_path(url_path)
            if params is None:
                continue
            method_allowed = route.match_method(method)
            if not method_allowed:
                allowed_methods.update(route.methods)
                _excs.append(MethodNotAllowed(allowed_methods))
                continue
            params.update(self.resources)
            try:
                ep_res = route.execute(request, **params)
                if not isinstance(ep_res, BaseResponse):
                    msg = 'expected Response, received %r' % type(ep_res)
                    raise InternalServerError(msg)
                return ep_res
            except Exception as e:
                if not isinstance(e, BaseResponse):
                    _, _, exc_traceback = sys.exc_info()
                    tbi = TracebackInfo.from_traceback(exc_traceback)
                    e = InternalServerError(traceback=tbi)
                _excs.append(e)
                if getattr(e, 'is_breaking', True):
                    break
        if _excs:
            return _excs[-1]
        return NotFound(is_breaking=False)


class SubApplication(object):
    def __init__(self, prefix, app, rebind_render=False):
        self.prefix = prefix.rstrip('/')
        self.app = app
        self.rebind_render = rebind_render

    def iter_routes(self, application, *a, **kw):
        # TODO: if `self.app` is `application` don't re-embed?
        for routes in self.app.iter_routes(application):
            for rt in routes.iter_routes(application):
                if isinstance(rt, NullRoute):
                    continue
                yld = rt.empty()
                yld.pattern = self.prefix + rt.pattern
                yield yld


"""
Notes
=====

TODO: divide up paths by HTTP method (minor optimization for match speed)
TODO: special handling for HTTPExceptions objects raised in debug mode
TODO: should TracebackInfo optionally know about exc_type and exc_msg?

Note to self: Raising and returning an exception should look basically the
same in production mode.
"""
