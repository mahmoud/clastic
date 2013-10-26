# -*- coding: utf-8 -*-

import sys
from collections import Sequence

from werkzeug.wrappers import BaseResponse
from werkzeug.wrappers import Request, Response

from .routing import BaseRoute, Route, NullRoute
from .tbutils import TracebackInfo
from .middleware import (check_middlewares,
                         merge_middlewares,
                         make_middleware_chain)
from ._errors import (BadRequest,
                      NotFound,
                      MethodNotAllowed,
                      InternalServerError)


RESERVED_ARGS = ('request', 'next', 'context', '_application', '_route')

S_REDIRECT = 'redirect'
S_NORMALIZE = 'normalize'
S_STRICT = 'strict'


def cast_to_rule_factory(in_arg):
    if isinstance(in_arg, BaseRoute):
        return in_arg
    # elif isinstance(in_arg, Rule):  # werkzeug backward compat desirable?
    #    ret = Route(in_arg.rule, in_arg.endpoint)
    #    ret.__dict__.update(in_arg.empty().__dict__)
    #    return ret
    elif isinstance(in_arg, Sequence):
        try:
            if isinstance(in_arg[1], BaseApplication):
                return SubApplication(*in_arg)
            if callable(in_arg[1]):
                return Route(*in_arg)
        except TypeError:
            pass
    # if isinstance(in_arg, RuleFactory):  # again, werkzeug backcompat wanted?
    #     return in_arg
    raise TypeError('Could not create routes from %r' % in_arg)


class BaseApplication(object):
    request_type = Request
    response_type = Response  # unused atm

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
        rf = cast_to_rule_factory(entry)
        rebind_render = getattr(rf, 'rebind_render', rebind_render)
        for route in rf.iter_routes(self):
            route.bind(self, rebind_render)
            self.routes.insert(index, route)
            index += 1

    def dispatch(self, request, slashes=S_NORMALIZE):
        "i know this looks weird, but parsing is always weird, i guess"
        # TODO: Precedence of MethodNotAllowed vs patterns. Do you
        # ever really check the POST of one pattern that much sooner
        # than the GET of the same pattern?

        # TODO: should returning an HTTPException and raising one have
        # basically the same behavior? more at 11pm.
        url = request.url
        method = request.method

        _excs = []
        allowed_methods = set()
        for route in self.routes:
            path_params = route.match_url(url)
            if path_params is None:
                continue
            method_allowed = route.match_method(method)
            if not method_allowed:
                allowed_methods.update(route.methods)
                _excs.append(MethodNotAllowed(allowed_methods))
                continue
            injectables = {'_route': route,
                           'request': request,
                           '_application': self}
            injectables.update(path_params)
            injectables.update(self.resources)
            try:
                ep_res = route.execute(**injectables)
                if not isinstance(ep_res, BaseResponse):
                    # TODO
                    msg = 'expected Response, received %r' % type(ep_res)
                    raise InternalServerError(msg)
            except Exception as e:
                #if self.debug:
                # TODO special rendering for HTTPException objects in debug
                #    raise
                if not isinstance(e, BaseResponse):
                    _, _, exc_traceback = sys.exc_info()
                    tbi = TracebackInfo.from_traceback(exc_traceback)
                    e = InternalServerError(tbi)
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

    def iter_routes(self, application, *a, *kw):
        # TODO: if `self.app` is `application` don't re-embed?
        for routes in self.app.iter_routes(application):
            for rt in routes.iter_routes(application):
                if isinstance(rt, NullRoute):
                    continue
                yld = rt.empty()
                yld.pattern = self.prefix + rt.pattern
                yield yld
