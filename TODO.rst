# TODO
======

Core
----
* raise exception on endpoint usage of builtin argument ``context`` or
  non-middleware usage of ``next``.

* nicer next() names
* polish sub-application mounting
* PyPI/packaging (mostly done)
* Sphinx docs
* MetaApplication styling and docs
* license

Contrib
-------
* Secure cookies/sessions
* JSON middleware
* Cache middleware
* Cline (bottle-like functionality)
* Example application
* Form processing middleware?

## v2
* Custom URL resolvers?
* Failsafe application reloading?
* Middleware <-> middleware merge hook?

## Chopping block
* Allowing duplicate middlewares
* endpoint_provides and render_provides

## Curiosities
* dynamic vs. static linked middleware stack performance
* OrderedSets?
* 'strict' mode with more immutability enforcement (immutable dicts
  for resources, etc.) and certain types of linting (detect unset
  global variables)
