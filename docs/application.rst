Applications and Routes
=======================

When it comes to Python and the web, the world speaks WSGI (`Web
Server Gateway Interface
<https://www.python.org/dev/peps/pep-0333/>`_). And a Clastic provides
exactly that: A WSGI :class:`Application`.

Clastic Applications are composed using Python code, plain and
simple. No decorators, no ``settings.py``, no special configuration
file. Just constructed objects, used to construct other objects.

Specifically, Applications consist of :ref:`Routes <routes>`,
Resources, :doc:`middleware`, and :ref:`error-handlers`.

The Application
---------------

.. autoclass:: clastic.Application
  :members:

.. _routes:

Route Types
-----------

.. autoclass:: clastic.Route
  :members:

.. autoclass:: clastic.GET

.. autoclass:: clastic.POST

.. autoclass:: clastic.PUT

.. autoclass:: clastic.DELETE

.. note::

  Method-specific subtypes have identical signatures to :class:`Route`.

  The only steps necessary to make a Route method-specific is to import the type and add it to the tuple::

    Application(routes=[("/home/", home_ep, render_func)])

  Becomes::

    from clastic import GET
    ...
    Application(routes=[GET("/home/", home_ep, render_func)])

If an Application contains Routes which match the path pattern, but
none of the Routes match the method, Clastic will automatically raise
a :class:`~clastic.MethodNotAllowed` exception for you, which results
in a ``405`` HTTP error response to client.

SubApplications
---------------

Clastic features strong composability using straightforward Python
constructs. An :class:`Application` contains :class:`Route` instances,
and those Routes can come from other Applications, using
:class:`SubApplication`.

.. autoclass:: clastic.SubApplication

.. _injectables:

Injectables
-----------

Clastic automatically provides dependencies to middlewares and
endpoint/render functions. These dependencies can come from one of
four sets:

1. **Route path pattern**
2. **Application resources** - Arguments which
   are valid for the lifespan of the :class:`Application`, like configuration variables.
3. **Middleware provides** - Arguments provided by an Application's
   middleware. See :doc:`middleware` for more information.
4. **Clastic built-ins** - Special arguments that are always made
   available by Clastic. These arguments are also reserved, and
   conflicting names will raise an exception. A list of these arguments
   and their meanings is below.


Clastic provides a small, but powerful set of built-in arguments for
every occasion. These arguments are reserved by Clastic, so know them
well.

.. note::

  Advanced and primarily-internal built-ins are prefixed with an
  underscore.

.. contents:: Built-in injectables
   :local:

.. _request-builtin:

request
^^^^^^^

   Probably the most commonly used built-in, ``request`` is the
   current ``Request`` object being handled by the Application. It has
   the URL arguments, POST parameters, cookies, user agent, other HTTP
   headers, and everything from the WSGI environ. :ref:`request-builtin`

.. _next-builtin:

next
^^^^

   ``next`` is only for use by Middleware, and represents the
   next function in the execution chain. It is called with the
   arguments the middleware class declared that it would provide. If
   the middleware does not provide any arguments, then it is called
   with no arguments.

   ``next`` allows a middleware to not worry about what middleware or
   function comes after it in the chain. All the middleware knows is
   that the result of (or exception raised by) the ``next`` function
   is the Response that a client would receive.

   Middleware functions must accept ``next`` as the first argument. If
   a middleware function does not accept the ``next`` argument, or if
   a non-middleware function accepts the ``next`` argument, an
   exception is raised at Application initialization.

.. _context-builtin:

context
^^^^^^^

   ``context`` is the output of the endpoint side of the middleware
   chain. By convention, it is almost always a dictionary of values
   meant to be used in templating or other sorts of Response
   serialization.

   Accepting the ``context`` built-in outside of the render branch of
   middleware will cause an exception to be raised at Application
   initialization. :ref:`context-builtin`

_application
^^^^^^^^^^^^

   The ``Application`` instance in which this middleware or endpoint
   is currently embedded. The Application has access to all routes,
   endpoints, middlewares, and other fun stuff, which makes
   ``_application`` useful for introspective activities, like those
   provided by Clastic's built-in ``MetaApplication``.

_route
^^^^^^

   The Route which was matched by the URL and is currently being
   executed. Also mostly introspective in nature. ``_route`` has a lot
   of useful attributes, such as ``endpoint``, which can be used to
   shortcut execution in an extreme case.

_error
^^^^^^

   Only available to the ``render_error`` functions/methods
   configured, this built-in is available when an :exc:`HTTPException`
   has been raised or returned.

_dispatch_state
^^^^^^^^^^^^^^^

   An internally-managed variable used by Clastic's
   routing machinery to generate useful errors. See
   :class:`DispatchState` for more info.

And, that's it! All other argument names are unreserved and yours for
the binding.


Clastic Routing in a Nutshell
-----------------------------

* Routes are always checked in the same order they were added to the
  Application. Some frameworks reorder routes, but not Clastic.
* Route methods must also match, or a :exc:`MethodNotAllowed` is raised.
* If a Route pattern matches, except for a trailing slash, the
  Application may redirect or rewrite the request, depending on the
  Application/Route's ``slash_mode``.

.. _pattern-minilanguage:

Pattern Mini-Language
---------------------

Route patterns use a minilanguage designed to minimize errors and
maximize readability, while compiling to Python regular expressions
remaining powerful and performant.

* Route patterns are a subset of regular expressions designed to match
  URL paths, and is thus aware of slashes. Slashes separate
  "segments", which can be one of three types: string, int, float.
* By default a pattern segment matches one URL path segment, but
  clastic also supports matching multiples of segments at once: (":"
  matches one segment, "?" matches zero or one segment, "*" matches 0
  or more segments, and "+" matches 1 or more segments).
* Segments are always named, and the names are checked against other
  injectables for conflicts.
* Be careful when getting too fancy with URL patterns. If your pattern
  doesn't match, by default users will see a relatively plain 404 page
  that does not offer much help as to why their URL is incorrect.

Advanced Routing
----------------

* Unlike Werkzeug/Flask's default routing, clastic does not reorder routes. Routes are matched in order.
* Applications can choose whether to redirect on trailing slashes
* Clastic's one-of-a-kind routing system allows endpoint functionsand middlewares to participate in routing by raising certain standard errors, telling clastic to continue to check other routes
* It's even possible to route to a separate WSGI application (i.e., an application not written in Clastic)
* NullRoute (configurable)


.. autoclass:: clastic.RerouteWSGI


.. autoclass:: clastic.application.DispatchState
