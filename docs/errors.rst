Errors
======

Errors matter in the HTTP/RESTful ecosystem.

Clastic offers a full set of exception types representing standard
HTTP errors, and a base HTTPException for creating your own exception
types.

The ``errors`` module also contains the Error Handler subsystem for
controlling how a Clastic Application behaves in error situations.

.. contents:: Contents
   :local:

.. _error_handlers:

Error Handlers
--------------

You can control how Clastic responds to various error scenarios by
creating or configuring an *Error Handler* and passing it to your
:class:`Application` instance.

Error Handlers are able to:

  * Control which specific error types are raised on routing failures
    (e.g., :class:`~clastic.errors.NotFound` and
    :class:`~clastic.errors.MethodNotAllowed`).
  * Control the error type which is raised when the endpoint or render
    function raises an uncaught exception (e.g.,
    :class:`~clastic.errors.InternalServerError`)
  * How uncaught exceptions are rendered or otherwise turned into HTTP Responses
  * Configure a WSGI middleware for the whole :class:`~clastic.Application`

The easiest way to control these behavior is to inherit from the
default :class:`ErrorHandler` and override the attributes or methods
you need to change:

.. autoclass:: clastic.errors.ErrorHandler
   :members:
   :undoc-members:

The default error handler presents the minimal detail to the client
when an error occurs.

Clastic ships with a couple special Error Handlers which it uses to
enable debuggability.

.. autoclass:: clastic.errors.ContextualErrorHandler
   :members: exc_info_type, not_found_type, server_error_type

.. autoclass:: clastic.errors.REPLErrorHandler


The Base HTTPException
----------------------

.. autoclass:: clastic.HTTPException

Standard HTTP Error Types
-------------------------

.. automodule:: clastic.errors
  :members:
  :undoc-members:
