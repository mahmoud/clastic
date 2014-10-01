
from .errors import (NotFound,
                     MethodNotAllowed,
                     InternalServerError,
                     MIME_SUPPORT_MAP)
from .tbutils import ExceptionInfo, ContextualExceptionInfo


def default_render_error(request, _error, **kwargs):
    best_match = request.accept_mimetypes.best_match(MIME_SUPPORT_MAP)
    _error.adapt(best_match)
    return _error


def default_uncaught_to_response(_application, route):
    eh = _application.error_handler
    if _application.debug:
        raise  # will use the werkzeug debugger 500 page

    exc_info = eh.exc_info_type.from_current()
    return eh.server_error_type(repr(exc_info),
                                traceback=exc_info,
                                source_route=route)


class RoutingErrorHandler(object):
    render_error = default_render_error

    # TODO: allow overriding redirects (?)

    # 404
    not_found_type = NotFound

    # 405
    method_not_allowed_type = MethodNotAllowed

    # 500
    exc_info_type = ExceptionInfo
    server_error_type = InternalServerError
    uncaught_to_response = default_uncaught_to_response

    def __init__(self, reraise_uncaught=False):
        self.reraise_uncaught = reraise_uncaught


class DebugRoutingErrorHandler(RoutingErrorHandler):
    exc_info_type = ContextualExceptionInfo
