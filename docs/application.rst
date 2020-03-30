Applications and Routes
=======================

*Coming soon!*

* Clastic Applications are constructed programmatically
* Applications consist of Routes, Resources, Middlewares, and Error Handlers
  * The latter two are discussed in :doc:`middlewares` and :doc:`errors`
* Routes consist of patterns, endpoint functions, and an optional render function
* Route patterns are a subset of regular expressions designed to match URL paths, and is thus aware of slashes. Slashes separate "segments", which can be one of three types: string, int, float.
* By default a pattern segment matches one URL path segment, but clastic also supports matching multiples of segments at once: (":" matches one segment, "?" matches zero or one segment, "*" matches 0 or more segments, and "+" matches 1 or more segments).
* Be careful when getting too fancy with URL patterns. If your pattern doesn't match, by default users will see a relatively plain 404 page that does not offer much help as to why their URL is incorrect.

* autodoc
  * Application
  * Route (+ GET/POST/PUT/DELETE/etc.)
  * SubApplication

The Application
---------------

.. autoclass:: clastic.Application
  :members:

Route Types
-----------

.. autoclass:: clastic.Route
  :members:

.. autoclass:: clastic.GET

.. autoclass:: clastic.POST

.. autoclass:: clastic.PUT

.. autoclass:: clastic.DELETE


SubApplications
---------------

Clastic features strong composability using straightforward Python
constructs. An :class:`Application` contains :class:`Route` instances,
and those Routes can come from other Applications, using
:class:`SubApplication`.

.. autoclass:: clastic.SubApplication



Advanced Routing
----------------

* Unlike Werkzeug/Flask's default routing, clastic does not reorder routes. Routes are matched in order.
* Applications can choose whether to redirect on trailing slashes
* Clastic's one-of-a-kind routing system allows endpoint functionsand middlewares to participate in routing by raising certain standard errors, telling clastic to continue to check other routes
* It's even possible to route to a separate WSGI application (i.e., an application not written in Clastic)
* NullRoute (configurable)

.. autoclass:: clastic.RerouteWSGI
