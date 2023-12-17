# -*- coding: utf-8 -*-

import os
import itertools
import sys
if sys.version_info < (3,3,):
    from collections import Sequence
else:
    from collections.abc import Sequence
from argparse import ArgumentParser

import attr
from werkzeug import test as werkzeug_test
from werkzeug.utils import redirect
from werkzeug.wrappers import Request, Response, BaseResponse

from .server import run_simple
from .route import (Route,
                    NullRoute,
                    S_STRICT,
                    S_REDIRECT,
                    RESERVED_ARGS,
                    normalize_path,
                    check_render_error)

from .utils import int2hexguid
from .middleware import check_middlewares
from .errors import (HTTPException,
                     MIME_SUPPORT_MAP,
                     ErrorHandler,
                     ContextualErrorHandler)
from .sinter import get_arg_names


try:
    unicode
except NameError:
    # py3
    unicode = str


_REQ_ID_ITER = itertools.count()


def cast_to_route_factory(in_arg):
    if isinstance(in_arg, (Route, SubApplication)):
        return in_arg
    elif isinstance(in_arg, Sequence):
        try:
            if isinstance(in_arg[1], Application):
                return SubApplication(*in_arg)
            if callable(in_arg[1]):
                return Route(*in_arg)
        except TypeError:
            pass
    raise TypeError('Could not create route from %r' % (in_arg,))


def default_render_error(request, _error, **kwargs):
    # TODO: remove in favor of DefaultErrorHandler?
    best_match = request.accept_mimetypes.best_match(MIME_SUPPORT_MAP)
    _error.adapt(best_match)
    return _error


def check_valid_wsgi(wsgi_callable):
    if not callable(wsgi_callable):
        raise TypeError('expected WSGI application (%r) to be callable'
                        % (wsgi_callable,))
    wc_args = get_arg_names(wsgi_callable)[:2]
    if (not len(wc_args) == 2
        or wc_args[0] != 'environ'
        or wc_args[1] != 'start_response'):
        raise TypeError('expected WSGI callable (%r)'
                        ' to accept two arguments, `environ` and'
                        ' `start_response`, respectively, not %r'
                        % (wsgi_callable, wc_args))
    return


def _get_all_middlewares(bound_routes):
    # TODO: use merge_middlewares
    all_mw = []

    for broute in reversed(bound_routes):
        for mw in broute.middlewares:
            # use list and eq so mws don't have to be hashable
            if mw not in all_mw:
                all_mw.append(mw)

    return all_mw


def _safe_wrap_wsgi(source_name, source, inner):
    wsgi_wrapper = getattr(source, 'wsgi_wrapper', None)
    if wsgi_wrapper is None:
        return inner  # no wsgi_wrapper, no problem
    elif not callable(wsgi_wrapper):
        raise TypeError('expected %s.wsgi_wrapper to be callable'
                        ' or None, not %r' % (source_name, wsgi_wrapper))

    wrapped_wsgi = wsgi_wrapper(inner)
    try:
        check_valid_wsgi(wrapped_wsgi)
    except TypeError as te:
        raise TypeError('expected valid WSGI callable from %s'
                        ' (%r) WSGI wrapper (%r), instead'
                        ' got issue: %r'
                        % (source_name, source, wsgi_wrapper, te))
    return wrapped_wsgi


# TODO: Possibly sticking an exception and an endpoint function is a
# bad idea, but it looks good and works from an API perspective
@attr.s(frozen=True)
class RerouteWSGI(Exception):
    """Raise or use as a route endpoint to route to a different WSGI app.

    Note that this will have unintended consequences if you have done
    stateful operations to the environ (such as reading the body of
    the request) or already called start_response or something
    similar.

    It's safest to put this high in the routing table (and middleware
    stack).
    """
    wsgi_app = attr.ib()

    def __call__(self):
        raise self


class Application(object):
    """The central object around which Clastic revolves.

    The Application initializer checks that all endpoints, render
    functions, and middlewares have their dependencies satisfied
    before completing construction. If the signatures don't line up,
    an :exc:`NameError` will be raised.

    Args:

      routes (list): A list of Route instances, SubApplications, or
        tuples. Defaults to ``[]``. Add more with :meth:`~Application.add()`.
      resources (dict): A dict which will be injectabled to Routes and
        middlewares in this Application. Keys must all be strings,
        values can be any Python object. Defaults to ``{}``.
      middlewares (list): A list of :doc:`middleware` objects.
        Defaults to ``[]``.
      render_factory (callable): An optional callable to convert
        render arguments into callables, such as
        :class:`~clastic.render.AshesRenderFactory`.
      debug (bool): Set to ``True`` to enable certain debug behavior in the application.
      error_handler: *Advanced*: An optional :ref:`ErrorHandler <error-handlers>` instance.
        Defaults to :class:`~clastic.errors.ErrorHandler`. If *debug* is
        ``True``, defaults to :class:`~clastic.errors.ContextualErrorHandler`.
      slash_mode (str): *Advanced*: Controls how the Application handles trailing slashes.
        One of :data:`clastic.S_REDIRECT`, :data:`~clastic.S_STRICT`, :data:`~clastic.S_REWRITE`.
        Defaults to :data:`~clastic.S_REDIRECT`.

    In addition to arguments, certain advanced behaviors can be
    customized by inheriting from :class:`Application` and overriding
    attributes: :attr:`~Application.request_type`,
    :attr:`~Application.response_type`,
    :attr:`~Application.default_error_handler_type`, and
    :attr:`~Application.default_debug_error_handler_type`.

    """
    request_type = Request
    response_type = Response
    default_error_handler_type = ErrorHandler
    default_debug_error_handler_type = ContextualErrorHandler

    def __init__(self, routes=None, resources=None, middlewares=None,
                 render_factory=None, error_handler=None, **kwargs):
        self.debug = kwargs.pop('debug', None)
        self.slash_mode = kwargs.pop('slash_mode', S_REDIRECT)
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

        self.set_error_handler(error_handler)

        routes = routes or []
        self.routes = []
        self._null_route = NullRoute().bind(self)
        for entry in routes:
            self.add(entry)

        all_mws = _get_all_middlewares(self.routes)
        for mw in reversed(all_mws):
            self._dispatch_wsgi = _safe_wrap_wsgi('middleware', mw, self._dispatch_wsgi)
        return

    def set_error_handler(self, error_handler=None):
        """Sets the :ref:`ErrorHandler <error-handlers>` instance. Call
        without arguments to reset the error handler to default.

        .. note::

          This method does not reset error handlers in Routes which have
          already been bound.
        """
        if error_handler is None:
            if self.debug:
                deh_type = self.default_debug_error_handler_type
            else:
                deh_type = self.default_error_handler_type
            error_handler = deh_type()
        check_render_error(error_handler.render_error, self.resources)
        self._dispatch_wsgi = _safe_wrap_wsgi('error_handler', error_handler, self._dispatch_wsgi)

        self.error_handler = error_handler

    def iter_routes(self):
        for rt in self.routes:
            yield rt

    def __repr__(self):
        cn = self.__class__.__name__
        ret = ('<%s routes_count=%s resources_keys=%r middlewares=%r render_factory=%r slash_mode=%r debug=%r>'
               % (cn, len(self.routes), list(self.resources.keys()), self.middlewares,
                  self.render_factory, self.slash_mode, self.debug))
        return ret

    def add(self, entry, index=None, **kwargs):
        """Add a :class:`Route` or :class:`SubApplication`. A tuple may also be
        passed, which will be converted accordingly.

        Note that as each Route is bound, the Application checks
        whether the Route's dependencies can be satisfied by the
        Application.
        """
        if index is None:
            index = len(self.routes)
        rf = cast_to_route_factory(entry)

        kwargs.setdefault('rebind_render', getattr(rf, 'rebind_render', True))
        kwargs.setdefault('inherit_slashes', getattr(rf, 'inherit_slashes', True))

        if callable(getattr(rf, 'bind_all', None)):
            bound_routes = rf.bind_all(self, **kwargs)
        else:
            bound_routes = [rf.bind(self, **kwargs)]
        for br in bound_routes:
            self.routes.insert(index, br)
            index += 1
        return

    def _dispatch_wsgi(self, environ, start_response):
        request = self.request_type(environ)
        try:
            # some request objects might not be amenable to assignment
            request.request_id = next(_REQ_ID_ITER)
        except Exception:
            pass
        else:
            request.request_guid = int2hexguid(request.request_id)
        try:
            response = self.dispatch(request)
        except RerouteWSGI as rre:
            return rre.wsgi_app(environ, start_response)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self._dispatch_wsgi(environ, start_response)

    def dispatch(self, request):
        ret = None
        url_path, method = request.path, request.method
        dispatch_state = DispatchState()
        err_handler = self.error_handler
        base_params = dict(self.resources,
                           request=request,
                           _application=self,
                           _dispatch_state=dispatch_state)

        for route in self.routes + [self._null_route]:
            path_params = route.match_path(url_path)
            if path_params is None:
                continue
            request.path_params = path_params
            params = dict(base_params, **path_params)
            method_allowed = route.match_method(method)
            if not method_allowed:
                dispatch_state.update_methods(route.methods)
                continue
            if route.is_branch:
                norm_path = normalize_path(url_path, route.is_branch)
                if norm_path != url_path:
                    if route.slash_mode == S_REDIRECT:
                        parts = [request.url_root.rstrip('/'),
                                 norm_path, '?', request.query_string.decode('utf8')]
                        return redirect(''.join(parts))  # TODO: error_handler
                    elif route.slash_mode == S_STRICT:
                        nf_exc = err_handler.not_found_type(request=request,
                                                            application=self,
                                                            source_route=route)
                        dispatch_state.add_exception(nf_exc)
                        continue
            try:
                ret = route.execute(**params)
                if not isinstance(ret, BaseResponse):
                    msg = 'expected Response, received %r' % type(ret)
                    raise TypeError(msg)
            except RerouteWSGI:
                raise
            except Exception as exc:
                ret = exc
                if not isinstance(ret, HTTPException):
                    uncaught_params = dict(params, _route=route, _error=ret)
                    ret = err_handler.uncaught_to_response(**uncaught_params)
            if not isinstance(ret, HTTPException):
                # TODO: verify behavior
                break
            if not getattr(ret, 'source_route', None):
                ret.source_route = route
            if getattr(ret, 'is_breaking', True):
                break
            else:
                dispatch_state.add_exception(ret)

        if isinstance(ret, HTTPException):
            error_params = dict(params, _error=ret)
            try:
                ret = ret.source_route.execute_error(**error_params)
            except Exception:
                ret = default_render_error(**error_params)
        return ret

    def get_local_client(self):
        """Get a simple local client suitable for using in tests. See
        `Werkzeug's test Client
        <https://werkzeug.palletsprojects.com/en/1.0.x/test/#werkzeug.test.Client>`_
        for more info.
        """
        return werkzeug_test.Client(self, Response)

    def serve(self,
              address='0.0.0.0',
              port=5000,
              use_meta=True,
              use_lint=True,
              use_reloader=True,
              use_debugger=True,
              use_static=True,
              static_prefix='static',
              static_path=None,
              processes=None,
              **kw):
        """Serve the Application locally, suitable for development purposes.

        Args:

           address (str): IP address to bind to (defaults to ``"0.0.0.0"``, which works for all IPs)
           port (int): Port to bind on (defaults to ``5000``)
           use_meta (bool): Whether to automatically add the
             :doc:`MetaApplication <meta_application>` to ``/_meta/``. Defaults to ``True``.
           use_reloader (bool): Whether to automatically reload the application when changes
             to the source code are saved. Defaults to ``True``.
           use_debugger (bool): Whether to wrap the Application in
             `werkzeug's debug middleware
             <https://werkzeug.palletsprojects.com/en/1.0.x/debug/>`_
             for interactive debugging. (Note that a PIN will be
             output on stdout and must be used to interact with the
             error pages.)
           use_static (bool): Whether to automatically serve
             *static_path* under *static_prefix*. Defaults to
             ``True``.
           static_prefix (str): The URL path where static assets will
             be served. Defaults to `/static/`.
           static_path (str): The filesystem path to static assets to
             serve if *use_static* is ``True``. Defaults to a path named
             "static" in the current directory (``"./static/"``).
           processes (int): Number of processes to serve (not
             recommended for use with *use_debugger*). (Use
             sparingly; not for production.)

        .. warning::

           The server provided by this method is not intended for production traffic use.
        """
        parser = create_dev_server_parser()
        args, _ = parser.parse_known_args()

        address = args.address or address
        port = args.port if args.port is not None else port
        kw['use_reloader'] = args.use_reloader and use_reloader
        kw['use_debugger'] = args.use_debugger and use_debugger
        if kw['use_debugger']:
            # TODO: if an error_handler doesn't respect
            # reraise_uncaught then the debugger won't work
            self.error_handler.reraise_uncaught = True
        kw['processes'] = args.processes or processes
        use_meta = args.use_meta and use_meta
        use_lint = args.use_lint and use_lint
        use_static = args.use_static and use_static

        if use_meta:
            from .meta import MetaApplication
            self.add(('/_meta/', MetaApplication()))
        if use_static:
            from .static import StaticApplication
            static_path = args.static_path or static_path or \
                os.path.join(os.getcwd(), 'static')
            static_prefix = args.static_prefix or static_prefix
            static_prefix = '/' + unicode(static_prefix).lstrip('/')
            static_app = StaticApplication(static_path)
            self.add((static_prefix, static_app), index=0)

        if kw.get('_jk_just_testing'):
            return True

        run_simple(address, port, self, **kw)


class DispatchState(object):
    """The every request handled by an :class:`Application` creates a
    :class:`DispatchState`, which is used to track relevant state in
    the routing progress, including which routes were attempted and
    what exceptions were raised, if any.


    .. note::

      Objects of this type are constructed internally and are not really
      part of the Clastic API, except that they are one of the built-in
      injectables.
    """

    def __init__(self):
        self.exceptions = []
        self.allowed_methods = set()
        self.attempted_routes = []

    def add_route(self, route):
        self.attempted_routes.append(route)

    def add_exception(self, exception):
        self.exceptions.append(exception)

    def update_methods(self, methods):
        if methods:
            self.allowed_methods.update(methods)

    def __repr__(self):
        args = (self.__class__.__name__, self.exceptions, self.allowed_methods)
        return '<%s exceptions=%r allowed_methods=%r>' % args


class SubApplication(object):
    """Enables :class:`Application` instances to be embedded in other Applications.

    Note that Routes are copied into the embedding Application, and further
    modifications to the Application after embedding may not be visible
    in the root Application.

    Args:

      prefix (str): The path prefix under which the embedded Application's routes
        will appear. ``/`` is valid, and will merge the routes in at the root level
        of the parent application.
      app (Application): The Application instance being embedded.
      rebind_render (bool): **Advanced**: Whether render arguments
        should be reinterpreted by the embedding application's render
        factory. Defaults to ``False``.
      inherit_slashes (bool): **Advanced**: Whether to inherit the
        embedding application's handling of trailing slashes. Defaults
        to ``True``.

    .. note::

       This object rarely needs to be constructed manually, because
       this behavior is built in to the default Application routes
       argument handling.
       ``Application(routes=[('/prefix', other_app)])``
       automatically creates a SubApplication and embeds it.

    """
    def __init__(self, prefix, app, rebind_render=False, inherit_slashes=True):
        self.prefix = prefix.rstrip('/')
        self.app = app
        self.rebind_render = rebind_render
        self.inherit_slashes = inherit_slashes

    def bind_all(self, app, **kwargs):
        # app is the new app to bind to, self.app is the subapp we're
        # going to pull routes from. could
        ret = []

        kwargs['prefix'] = self.prefix
        kwargs.setdefault('rebind_render', self.rebind_render)
        kwargs.setdefault('inherit_slashes', self.inherit_slashes)

        for rt in self.app.routes:
            if isinstance(rt, NullRoute):
                continue
            bound_rt = rt.bind(app, **kwargs)
            ret.append(bound_rt)

        return ret

    def iter_routes(self):
        for rt in self.app.iter_routes():
            if isinstance(rt, NullRoute):
                continue
            yield rt
        return


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

"""
Notes
=====

TODO: divide up paths by HTTP method (minor optimization for match speed)
TODO: special handling for HTTPExceptions objects raised in debug mode
TODO: should TracebackInfo optionally know about exc_type and exc_msg?

Redirecting on a non-GET request can lead to a confusing error,
because redirects only yield GET responses. Maybe don't normalize
slashes on POST and such?

Note to self: Raising and returning an exception should look basically the
same in production mode.

Potentially conflicting rebindables:

* render (green-path and red)
* slash behavior
* debug flag
"""

"""
all_mw = IndexedSet()

for broute in reversed(self._bound_routes):
    for mw in broute.middlewares:
        all_mw.add(mw)

all_wsgi_mw = IndexedSet()
for mw in all_mw:
    all_wsgi_mw.extend(mw.wsgi_mws)
"""
