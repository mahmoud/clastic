# -*- coding: utf-8 -*-

from werkzeug.exceptions import *


'''
Most sites, especially production sites, need to tightly control which
errors are exposed to users, for both security and usability purposes.
Error handlers provide this functionality for Clastic. They're like a
fallback endpoint for when an exception gets raised during the course
of executing the normal endpoint and middlewares.

When Clastic encounters an exception raised from an endpoint, it
checks the exception for an attached HTTP status code. If found,
Clastic checks for an associated error handler on the application,
which it can then execute with the arguments detailed below.

If the exception is not an HTTPException with an associated status
code, or the code has no associated handler, Clastic makes one final
check for a handler registered under 'None'. If nothing matches at
this point, Clastic just reraises the exception.

Technically, error handling is literally implemented as a big
try/except block around the endpoint/middleware chain, so your
endpoint and middlewares all have the opportunity to handle the errors
as they see fit; error handlers, when set, are a last-resort catchall.

Error handlers are dependency injected, just like, so they take
anywhere from zero to three arguments, in any order, as long as they
are named 'error', 'request', and/or '_application'. Note the
constrained argument list. Fewer arguments are made available to
account for the unsure state of the request/origin of the exception.
Handlers are expected to create and return their own HTTP response
objects; results are not rerun through any render phases.

Error handler maps are just simple dictionaries that are typically
passed into the Application constructor. The make_error_handler_map()
utility function below can make it a bit more safe and convenient to
construct such maps.

TODO: currently endpoint argument names are not sinter-checked.
TODO: subapplications do not keep their error handlers when
      copied/bound into parent applications.
'''


def make_error_handler_map(handler_map=None,
                           default_400=None,
                           default_500=None,
                           default_exc=None):
    handler_map = dict(handler_map or {})
    ret = {}
    if default_400:
        if not callable(default_400):
            raise TypeError('default_400 expected function, not %r'
                            % default_400)
        for code in range(400, 419):
            ret[code] = default_400

    if default_500:
        if not callable(default_500):
            raise TypeError('default_500 expected function, not %r'
                            % default_500)
        for code in range(500, 504):
            ret[code] = default_500

    if default_exc:
        if not callable(default_exc):
            raise TypeError('default_exc expected function, not %r'
                            % default_exc)
        ret[None] = default_exc

    if handler_map:
        for code, handler in handler_map.items():
            if not callable(handler):
                raise TypeError('error %s handler expected function, not %r'
                                % (code, default_500))
            ret[code] = handler

    return ret
