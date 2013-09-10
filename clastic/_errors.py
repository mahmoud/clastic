# -*- coding: utf-8 -*-


class HTTPException(object):
    status_code = None
    description = ''


class BadRequest(HTTPException):
    code = 400


class InternalServerError(HTTPException):
    code = 500


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


class NotImplemented(InternalServerError):
    code = 501


class BadGateway(InternalServerError):
    code = 502


class ServiceUnavailable(InternalServerError):
    code = 503
