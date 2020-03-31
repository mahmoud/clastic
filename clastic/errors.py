# -*- coding: utf-8 -*-
"""In addition to error handling mechanisms, ``clastic.error`` ships
with exception types for every standard HTTP error.

Because these standard error types inherit from
:class:`HTTPException`, which is both an exception and a Response
type, they can be raised or returned.

Errors are organized by error code, in ascending order. Note that the
``message`` attribute is sometimes called the "name", e.g. "Not Found"
for ``404``.

"""


"""
One notable (if incremental) improvement over Werkzeug's error system
is that 400-level requests share a common base class
(BadRequest). Same goes for do 500-coded requests
(InternalServerError).

Another note: If you subclass any of these errors, make sure
the __init__ accepts **kwargs.
"""

"""
Clastic HTTP exceptions seek to provide a general structure for errors
that readily translates to common human- and machine-readable formats
(i.e., JSON, XML, HTML, plain text). It does so with the following
fields:

- code (required): Defines the fundamental class of error, as
  according to the HTTP spec, usually implied by the HTTPException
  subclass being used
- message: A short message describing the error, defaulting to
  the one specified by HTTP (e.g., 403 -> "Forbidden",
  404 -> "Not Found")
- detail: A longer-form description of the message, used as
  the body of the response. Could include an explanation of the error,
  trace information, or unique identifiers. Structured values
  will be JSON-ified.
- error_type: A short value specifying the specific subtype of HTTP
  (e.g., for 403, "http://example.net/errors/invalid_token")

TODO: naming scheme?
TODO: HTTPException could well be a metaclass
TODO: weird print/repr bug (prints blank)
TODO: enable detail to be a templatable thing?
TODO: 500-level errors should support a structured traceback field?

Possible values to support templating:

* Target URL
* Referring URL
* Method
* Allowed methods

"""
import sys
import datetime
try:
    import exceptions
    from cgi import escape as html_escape
    PY_VERSION = 2
except ImportError:
    unicode = str
    import builtins as exceptions  # lol py3
    from html import escape as html_escape
    PY_VERSION = 3

from werkzeug.utils import get_content_type
from werkzeug.debug import DebuggedApplication
from werkzeug.wrappers import BaseResponse
from boltons.tbutils import ExceptionInfo, ContextualExceptionInfo
from glom import glom, T

from . import _version
from .render.simple import ClasticJSONEncoder
from ._contextual_errors import CONTEXTUAL_ENV


ERROR_CODE_MAP = None
STDLIB_EXC_URL = 'http://docs.python.org/%s/library/exceptions.html#exceptions.' % PY_VERSION


__all__ = []  # for docs purposes, gets inited by _module_init


def _module_init():
    global __all__
    global ERROR_CODE_MAP
    ERROR_CODE_MAP = {}
    for k, v in globals().items():
        try:
            if issubclass(v, HTTPException):
                ERROR_CODE_MAP[v.code] = v
        except (TypeError, AttributeError):
            pass

    __all__.extend([v.__name__ for k, v in
                    sorted(ERROR_CODE_MAP.items(),
                           key=lambda x: x[1].code or 0)
                    if k])


MIME_SUPPORT_MAP = {'text/html': 'html',
                    'application/json': 'json',
                    'text/plain': 'text',
                    'application/xml': 'xml'}
DEFAULT_MIME = 'text/plain'


class HTTPException(BaseResponse, Exception):
    """The base :class:`Exception` for all default HTTP errors in this
    module, the HTTPException also inherits from
    :class:`BaseResponse`, making instances of it and its subtypes
    valid to use via raising, as well as returning from endpoints and
    render functions.

    Args:

      detail (str): A string with information about the
        exception. Appears in the body of the HTML error page.
      code (int): A numeric HTTP status code (e.g., ``400`` or ``500``).
      message (str): A short name for the error, (e.g., ``"Not Found"``)
      error_type (str): An error type name **or link** to a page with
        details about the type of error. Useful for linking to docs.
      is_breaking (bool): *Advanced*: For integrating with Clastic's
        routing system, set to ``True`` to specify that this error
        instance should not preempt trying routes further down the
        routing table. If no other route matches or succeeds, this
        error will be raised.
      source_route (Route): *Advanced*: The route instance that raised this exception.
      mimetype (str): A MIME type to return in the Response headers.
      content_type (str): A Content-Type to return in the Response headers.
      headers (dict): A mapping of custom headers for the Response. Defaults to ``None``.


    .. note::

      The base HTTPException includes simple serialization to text,
      HTML, XML, and JSON.  So if a client requests a particular
      format (using the ``Accept`` header), it will automatically
      respond in that format. It defaults to ``text/plain`` if the
      requested MIME type is not recognized.

    """

    code = None
    message = 'Error'
    detail = 'An unspecified error occurred.'

    def __init__(self, detail=None, **kwargs):
        self.detail = detail or self.detail
        self.message = kwargs.pop('message', self.message)
        self.code = kwargs.pop('code', self.code)
        self.error_type = kwargs.pop('error_type', None)
        self.is_breaking = kwargs.pop('is_breaking', True)
        self.source_route = kwargs.pop('source_route', None)

        headers = kwargs.pop('headers', None)
        mimetype = kwargs.pop('mimetype', DEFAULT_MIME)
        content_type = kwargs.pop('content_type', None)
        super(HTTPException, self).__init__(response=self.to_text(),
                                            status=self.code,
                                            headers=headers,
                                            mimetype=DEFAULT_MIME,
                                            content_type=content_type)
        if mimetype != DEFAULT_MIME:
            self.adapt(mimetype)
        return

    def adapt(self, mimetype=None):
        try:
            fmt_name = MIME_SUPPORT_MAP[mimetype]
        except KeyError:
            fmt_name, mimetype = 'text', 'text/plain'
        _method = getattr(self, 'to_' + fmt_name)
        self.data = _method()
        self.headers['Content-Type'] = get_content_type(mimetype, self.charset)

    def transcribe(self, request):
        # TODO
        # create a new Response object with content and headers
        # adapted to Accept headers
        pass

    def to_dict(self):
        ret = {'detail': self.detail,
               'message': self.message,
               'code': self.code,
               'error_type': self.error_type}
        return ret

    def to_escaped_dict(self):
        ret = {}
        for k, v in self.to_dict().items():
            if v is None:
                ret[k] = ''
                continue
            try:
                ret[k] = html_escape(v, True)
            except Exception as e:
                ret[k] = html_escape(repr(v), True)
        return ret

    def to_json(self, indent=2, sort_keys=True, skipkeys=True):
        encoder = ClasticJSONEncoder(dev_mode=True, indent=indent,
                                     sort_keys=sort_keys, ensure_ascii=False,
                                     skipkeys=skipkeys)
        return encoder.encode(self.to_dict())

    def to_text(self):
        lines = ['%s - %s' % (self.code, self.message)]
        if self.detail:
            lines.extend(['', self.detail])
        if self.error_type:
            lines.extend(['', 'Error type: %s' % self.error_type])
        return '\n'.join(lines)

    def to_html(self):
        params = self.to_escaped_dict()
        lines = ['<!doctype html><html>',
                 '<head><title>{code} - {message}</title></head>',
                 '<body><h1>{message}</h1>']
        if params['detail']:
            lines.append('<p>{detail}</p>')
        if params['error_type']:
            if params['error_type'].startswith('http'):
                lines.append('<p>Error type: '
                             '<a target="_blank" href="{error_type}">'
                             '{error_type}</a></p>')
            else:
                lines.append('<p>Error type: {error_type}</p>')
        lines.append('</body></html>')
        return '\n'.join(lines).format(**params)

    def to_xml(self):
        # TODO: generically create xml based on escaped dictionary
        params = self.to_escaped_dict()
        ret = ('<http_error>'
               '<code>{code}</code>'
               '<message>{message}</message>'
               '<detail>{detail}</detail>'
               '<error_type>{error_type}</error_type>'
               '</http_error>').format(**params)
        return ret

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(message=%r)' % (cn, getattr(self, 'message', ''))

    def __str__(self):
        if not self.detail:
            ret = self.message
        elif isinstance(self.detail, unicode):
            ret = self.detail
        else:
            ret = repr(self.detail)
        if len(ret) > 512:
            ret = ret[:256] + '...' + ret[-253:]

        return ret


class BadRequest(HTTPException):
    code = 400
    message = "Bad Request"
    detail = ("Your web client or proxy sent a request"
              " that this endpoint could not understand.")


class Unauthorized(BadRequest):
    code = 401
    message = "Authentication required"
    detail = ("The endpoint could not verify that your client"
              " is authorized to access this resource. Check"
              " that your client is capable of authenticating"
              " and that the proper credentials were provided.")


class PaymentRequired(BadRequest):
    "HTTP cares about your paywall."
    code = 402
    message = "Payment required"
    detail = ("This endpoint requires payment. Money doesn't"
              " grow on HTTPs, you know.")


class Forbidden(BadRequest):
    code = 403
    message = "Access forbidden"
    detail = ("You don't have permission to access the requested"
              " resource.")


class NotFound(BadRequest):
    code = 404
    message = "Not found"
    detail = "The requested URL was not found on this server."

    def __init__(self, *args, **kwargs):
        self.dispatch_state = kwargs.get('dispatch_state', None)
        super(NotFound, self).__init__(*args, **kwargs)


class MethodNotAllowed(BadRequest):
    code = 405
    message = "Method not allowed"
    detail = "The method used is not allowed for the requested URL."

    def __init__(self, allowed_methods=None, *args, **kwargs):
        self.allowed_methods = set(allowed_methods or [])
        # TODO: should go after super call?
        if self.allowed_methods:
            method_list = sorted(self.allowed_methods)
            self.detail = '%s Allowed methods: %r' % (self.detail,
                                                      method_list)
        super(MethodNotAllowed, self).__init__(*args, **kwargs)


class NotAcceptable(BadRequest):
    code = 406
    message = "Available content not acceptable"
    detail = ("The endpoint cannot generate a response acceptable"
              " by your client (as specified by your client's"
              " Accept header values).")


class ProxyAuthenticationRequired(BadRequest):
    code = 407
    message = "Proxy authentication required"
    detail = ("A proxy between your server and the client requires"
              " authentication to access this resource.")


class RequestTimeout(BadRequest):
    code = 408
    message = "Request timed out"
    detail = ("The server cancelled the request because the client"
              " did not complete the request within the alotted time.")


class Conflict(BadRequest):
    code = 409
    message = "A conflict occurred"
    detail = ("The endpoint cancelled the request due to a potential"
              " conflict with existing server state, such as a"
              " duplicate filename.")


class Gone(BadRequest):
    code = 410
    message = "Gone"
    detail = ("The requested resource is no longer available on this"
              " server and there is no forwarding address.")


class LengthRequired(BadRequest):
    code = 411
    message = "Length required"
    detail = ("A request for this resource is required to have a"
              " valid Content-Length header.")


class PreconditionFailed(BadRequest):
    code = 412
    message = "Precondition failed"
    detail = ("A required precondition on the request for this"
              " resource failed positive evaluation.")


class RequestEntityTooLarge(BadRequest):
    code = 413
    message = "Request entity too large"
    detail = ("The method/resource combination requested does"
              " not allow data to be transmitted, or the data"
              " volume exceeds the capacity limit.")


class RequestURITooLong(BadRequest):
    code = 414
    message = "Request URL too long"
    detail = ("The length of the requested URL exceeds the"
              " limit for this endpoint/server.")


class UnsupportedMediaType(BadRequest):
    code = 415
    message = "Unsupported media type"
    detail = ("The server does not support the media type"
              " transmitted in the request. Try a different media"
              " type or check your Content-Type header and try again.")


class RequestedRangeNotSatisfiable(BadRequest):
    code = 416
    message = "Requested range not satisfiable"
    detail = ("The client sent a ranged request not fulfillable by"
              " this endpoint.")


class ExpectationFailed(BadRequest):
    "Can't. always. get. what you want."
    code = 417
    message = "Expectation failed"
    detail = ("The server could not meet the requirements indicated in"
              " the request's Expect header(s).")


class ImATeapot(BadRequest):
    "Standards committees are known for their senses of humor."
    code = 418
    message = "I'm a teapot: short, stout."
    detail = ("This server is a teapot, not a coffee machine, and would"
              " like to apologize in advance if it is a Java machine.")


class UnprocessableEntity(BadRequest):
    code = 422
    message = "Unprocessable entity"
    detail = ("The client sent a well-formed request, but the endpoint"
              " encountered other semantic errors within the data.")


class UpgradeRequired(BadRequest):
    "Used to upgrade connections (to TLS, etc., RFC2817). Also WebSockets."
    code = 426
    message = "Upgrade required"
    detail = ("The server requires an upgraded connection to continue."
              " This is expected behavior when establishing certain"
              " secure connections or WebSockets.")


class PreconditionRequired(BadRequest):
    code = 428
    message = "Precondition required"
    detail = ("This endpoint requires a request with a conditional clause."
              " Try resubmitting the request with an 'If-Match' or "
              " 'If-Unmodified-Since' HTTP header.")


class TooManyRequests(BadRequest):
    code = 429
    message = "Too many requests"
    detail = ("The client has exceeded the allowed rate of requests for"
              " this resource. Please wait and try again later.")


class RequestHeaderFieldsTooLarge(BadRequest):
    code = 431
    message = "Request header fields too large"
    detail = ("One or more HTTP header fields exceeded the maximum"
              " allowed size.")


class UnavailableForLegalReasons(BadRequest):
    "Sit back and enjoy the Bradbury"
    code = 451
    message = "Unavailable for legal reasons"
    detail = ("The resource requested is unavailable for legal reasons."
              " For instance, this could be due to intellectual property"
              " claims related to copyright or trademark, or government"
              "-mandated censorship.")
#
# 500s below
#


class InternalServerError(HTTPException):
    code = 500
    message = "Internal server error"
    detail = ("The server encountered an internal error and was unable"
              " to complete your request.")

    def __init__(self, detail=None, **kwargs):
        self.exc_info = kwargs.pop('exc_info', None)
        super(InternalServerError, self).__init__(detail, **kwargs)
        if self.error_type is None:
            try:
                exc_type_name = self.exc_info.exc_type
                exc_type = getattr(exceptions, exc_type_name)
                self.error_type = STDLIB_EXC_URL + exc_type.__name__
            except Exception:
                pass

    def to_dict(self):
        ret = super(InternalServerError, self).to_dict()
        ret['exc_info'] = glom(self, T.exc_info.to_dict(), skip_exc=Exception)
        return ret


class NotImplemented(InternalServerError):
    code = 501
    message = "Response behavior not implemented"
    detail = ("The resource requested has either not been implemented or"
              " does not yet support the action requested by the client.")


class BadGateway(InternalServerError):
    code = 502
    message = "Bad gateway"
    detail = ("The endpoint received an invalid response from an upstream"
              " server while processing your request. Check that all"
              " upstream dependencies are properly configured and running.")


class ServiceUnavailable(InternalServerError):
    code = 503
    message = "Service or resource unavailable"
    detail = ("The service or resource requested is temporarily unavailable"
              " due to maintenance downtime or capacity issues. Please try"
              " again later.")


class GatewayTimeout(InternalServerError):
    code = 504
    message = "Gateway timeout"
    detail = ("The endpoint timed out while waiting for a response from an"
              " upstream server. check that all upstream dependencies are"
              " properly configured and running.")


class HTTPVersionNotSupported(InternalServerError):
    code = 505
    message = "HTTP version not supported"
    detail = ("The endpoint does not support the version of HTTP specified"
              " by the request.")


## START ERROR HANDLER

class ErrorHandler(object):
    """The default Clastic error handler. Provides minimal detail,
    suitable for a production setting.

    Args:

      reraise_uncaught (bool): Set to `True` if you want uncaught
        exceptions to be handled by the WSGI server rather than by this
        Clastic error handler.

    """

    wsgi_wrapper = None

    # TODO: allow overriding redirects (?)

    # 404
    not_found_type = NotFound

    # 405
    method_not_allowed_type = MethodNotAllowed

    # 500
    exc_info_type = ExceptionInfo
    server_error_type = InternalServerError

    def __init__(self, **kwargs):
        self.reraise_uncaught = kwargs.get('reraise_uncaught')

    def render_error(self, request, _error):
        """
        Turn an :exc:`HTTPException` into a Response of your

        Like endpoints and render functions, ``render_error()`` supports
        injection of any built-in arguments, as well as the `_error`
        argument (an instance of :exc:`HTTPException`, so feel free to
        adapt the signature as needed.

        This method is attached to Routes as they are bound into
        Applications. Routes can technically override this behavior,
        but generally a Route's error handling reflects that of the
        Error Handler in the root application where it is bound.

        By default this method just adapts the response between text,
        HTML, XML, and JSON.

        """
        best_match = request.accept_mimetypes.best_match(MIME_SUPPORT_MAP)
        _error.adapt(best_match)
        return _error

    def uncaught_to_response(self, _application, _route, **kwargs):
        """Called in the ``except:`` block of Clastic's routing. Must take the
        currently-being-handled exception and **return** a response
        instance. The default behavior returns an instance of whatever
        type is set in the `server_error_type` attribute
        (:class:`InternalServerError`, by default).

        Note that when inheriting, the method signature should accept
        ``**kwargs``, as Clastic does not inject arguments as it does
        with endpoint functions, etc.

        """
        if self.reraise_uncaught:
            raise
        eh = _application.error_handler
        exc_info = eh.exc_info_type.from_current()
        return eh.server_error_type(repr(exc_info),
                                    exc_info=exc_info,
                                    source_route=_route)


class ContextualInternalServerError(InternalServerError):
    """\
    An Internal Server Error with a full contextual view of the
    exception, mostly for development (non-production) purposes.

    # NOTE: The dict returned by to_dict is not JSON-encodable with
    the default encoder. It relies on the ClasticJSONEncoder currently
    used in the InternalServerError class.
    """
    def __init__(self, *a, **kw):
        self.request = kw.get('request')
        self.hide_internal_frames = kw.pop('hide_internal_frames', True)
        super(ContextualInternalServerError, self).__init__(*a, **kw)

    def to_dict(self, *a, **kw):
        ret = super(ContextualInternalServerError, self).to_dict(*a, **kw)
        del ret['exc_info']
        exc_info = getattr(self, 'exc_info', None)
        if not exc_info:
            return ret
        exc_tb = exc_info.tb_info.to_dict()
        for i, frame in enumerate(exc_tb['frames']):
            if self.hide_internal_frames:
                if not frame['line'] and frame['module_path'] == '<string>':
                    frame['is_hidden'] = True
                elif frame['module_name'] == 'clastic.sinter' and \
                     frame['func_name'] == 'inject':
                    frame['is_hidden'] = True
            frame['id'] = i
            pre_start_lineno = glom(frame, T['pre_lines'][0]['lineno'], default=1)
            frame['pre_start_lineno'] = pre_start_lineno
            frame['post_start_lineno'] = frame['lineno'] + 1

        last_frame = glom(exc_tb, T['frames'][-1], default=None)


        eid = {'is_email': False,
               'clastic_version': _version.__version__,
               'exc_type': exc_info.exc_type,
               'exc_value': exc_info.exc_msg,
               'exc_tb': exc_tb,
               'last_frame': last_frame,
               'exc_tb_str': str(exc_info.tb_info),
               'server_time': str(datetime.datetime.now()),
               'server_time_utc': str(datetime.datetime.utcnow()),
               'python': {'executable': sys.executable,
                          'version': sys.version.replace('\n', ' '),
                          'path': sys.path}}
        request = self.request
        if request:
            eid['req'] = {'path': request.path,
                          'full_url': request.url,
                          'method': request.method,
                          'abs_path': request.path,
                          'url_params': request.args,
                          'cookies': request.cookies,
                          'headers': request.headers,
                          'files': request.files}
        ret.update(eid)
        return ret

    def to_html(self, *a, **kw):
        render_ctx = self.to_dict()
        return CONTEXTUAL_ENV.render('500.html', render_ctx)


class ContextualNotFound(NotFound):

    def __init__(self, *a, **kw):
        self.request = kw.get('request')
        self.application = kw.get('application')
        self.dispatch_state = kw.get('dispatch_state')
        super(ContextualNotFound, self).__init__(*a, **kw)

    def to_dict(self):
        """
        One design ideal, for showing which routes have been hit:
        [{'route': ('pattern', 'endpoint', 'render_func'),
          'path_matched': False,
          'method_matched': False,
          'slash_matched': False}]
        """
        ret = super(ContextualNotFound, self).to_dict()
        app = self.application
        if not app:
            return ret

        route_results = []
        for route in app.routes:
            cur = {'pattern': route.pattern,
                   'regex': route.regex.pattern}
            if route.methods:
                cur['methods'] = sorted(route.methods)
            route_results.append(cur)
        ret['routes'] = route_results
        if self.request:
            ret['request'] = _req = {}
            _req['path'] = self.request.path
            _req['method'] = self.request.method
        return ret

    def to_html(self, *a, **kw):
        render_ctx = self.to_dict()
        return CONTEXTUAL_ENV.render('404.html', render_ctx)


class ContextualErrorHandler(ErrorHandler):
    """An error handler which offers a bit of debugging context,
    including a stack and locals (for server errors) and routes tried
    (for 404s).

    Might be OK for some internal tools, but should generally not be
    used for production.

    """

    exc_info_type = ContextualExceptionInfo
    server_error_type = ContextualInternalServerError

    not_found_type = ContextualNotFound

    def __init__(self, *a, **kw):
        self.hide_internal_frames = kw.pop('hide_internal_frames', True)
        super(ContextualErrorHandler, self).__init__(*a, **kw)

    def uncaught_to_response(self, _application, _route, **kwargs):
        eh = _application.error_handler
        exc_info = eh.exc_info_type.from_current()
        SEType = eh.server_error_type
        return SEType(repr(exc_info),
                      exc_info=exc_info,
                      source_route=_route,
                      request=kwargs.get('request'),
                      hide_internal_frames=self.hide_internal_frames)


class _REPLDebuggedApplication(DebuggedApplication):
    def __init__(self, app, **kwargs):
        kwargs['evalex'] = True
        super(_REPLDebuggedApplication, self).__init__(app, **kwargs)


class REPLErrorHandler(ContextualErrorHandler):
    """This error handler wraps the Application in a `Werkzeug debug
    middleware <https://werkzeug.palletsprojects.com/en/1.0.x/debug/>`_.

    """

    wsgi_wrapper = _REPLDebuggedApplication

    def uncaught_to_response(self, **kwargs):
        raise


## END ERROR HANDLER

_module_init()
