# -*- coding: utf-8 -*-

import sys

from werkzeug.wrappers import BaseResponse
from werkzeug.wrappers import Request, Response

from .routing import BaseRoute
from .tbutils import TracebackInfo
from .middleware import (check_middlewares,
                         merge_middlewares,
                         make_middleware_chain)
from ._errors import (BadRequest,
                      NotFound,
                      MethodNotAllowed,
                      InternalServerError)


RESERVED_ARGS = ('request', 'next', 'context', '_application', '_route')


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
        for route in rf.get_rules(self.wmap):
            self._add_route(route, index, rebind_render)
            index += 1

    def add(self, route, *args, **kwargs):
        if not isinstance(route, BaseRoute):
            # for when a basic pattern is passed in
            route = BaseRoute(route, *args, **kwargs)
        self._route_list.append(route)

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
        for route in self._route_list:
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
