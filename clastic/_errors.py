# -*- coding: utf-8 -*-

"""
One notable (if incremental) improvement over Werkzeug's error system
is that 400-level requests share a common base class
(BadRequest). Same goes for do 500-coded requests
(InternalServerError).
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
TODO: enable detail to be a templatable thing?

Possible values to support templating:

* Target URL
* Referring URL
* Method
* Allowed methods

"""

from werkzeug.wrappers import BaseResponse


class HTTPException(BaseResponse, Exception):
    code = None
    message = 'Error'
    detail = 'An unspecified error occurred.'

    def __init__(self, detail=None, **kwargs):
        # TODO: detail could be streamed
        self.detail = detail or self.detail
        self.message = kwargs.pop('message', self.message)
        self.code = kwargs.pop('code', self.code)
        self.error_type = kwargs.pop('error_type', None)
        self.is_breaking = kwargs.pop('is_breaking', True)

        headers = kwargs.pop('headers', None)
        mimetype = kwargs.pop('mimetype', None)
        content_type = kwargs.pop('content_type', None)
        super(HTTPException, self).__init__(response=self.detail,
                                            status=self.code,
                                            headers=headers,
                                            mimetype=mimetype,
                                            content_type=content_type)


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
    message = "Resource not found"
    detail = "The requested URL was not found on this server."


class MethodNotAllowed(BadRequest):
    code = 405
    message = "Method not allowed"
    detail = "The method used is not allowed for the requested URL."


class NotAcceptable(BadRequest):
    code = 406
    message = "Available content not acceptable"
    detail = ("The endpoint cannot generate a response acceptable"
              " by your client (as specified by your client's"
              " Accept header values.")


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
    "more like ErrorNameTooLong, amirite?"
    code = 413
    message = "Request entity too large"
    detail = ("The method/resource combination requested does"
              " not allow data to be transmitted, or the data"
              " volume exceeds the capacity limit.")


class RequestURITooLong(BadRequest):
    "... shit."
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


if __name__ == '__main__':
    print GatewayTimeout()
