# -*- coding: utf-8 -*-

"""
One notable (if incremental) improvement over Werkzeug's error system
is that 400-level requests share a common base class
(BadRequest). Same goes for do 500-coded requests
(InternalServerError).
"""

from werkzeug.wrappers import BaseResponse


class HTTPException(BaseResponse, Exception):
    code = None
    description = ''


class BadRequest(HTTPException):
    code = 400


class Unauthorized(BadRequest):
    code = 401


class PaymentRequired(BadRequest):
    "HTTP cares about your paywall."
    code = 402


class Forbidden(BadRequest):
    code = 403


class NotFound(BadRequest):
    code = 404


class MethodNotAllowed(BadRequest):
    code = 405


class NotAcceptable(BadRequest):
    code = 406


class ProxyAuthenticationRequired(BadRequest):
    code = 407


class RequestTimeout(BadRequest):
    code = 408


class Conflict(BadRequest):
    code = 409


class Gone(BadRequest):
    code = 410


class LengthRequired(BadRequest):
    code = 411


class PreconditionFailed(BadRequest):
    code = 412


class RequestEntityTooLarge(BadRequest):
    "more like ErrorNameTooLong, amirite?"
    code = 413


class RequestURITooLong(BadRequest):
    "... shit."
    code = 414


class UnsupportedMediaType(BadRequest):
    code = 415


class RequestedRangeNotSatisfiable(BadRequest):
    code = 416


class ExpectationFailed(BadRequest):
    "Can't. always. get. what you want."
    code = 417


class InternalServerError(HTTPException):
    code = 500


class NotImplemented(InternalServerError):
    code = 501


class BadGateway(InternalServerError):
    code = 502


class ServiceUnavailable(InternalServerError):
    code = 503


class GatewayTimeout(InternalServerError):
    code = 504


class HTTPVersionNotSupported(InternalServerError):
    code = 505
