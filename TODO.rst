# TODO
======

Core
----
* raise exception on endpoint usage of builtin argument ``context``

* nicer next() names
* polish sub-application mounting
* PyPI/packaging (mostly done)
* docs
* dev/meta application
* license

Contrib
-------
* Secure cookies/sessions
* JSON middleware
* Cache middleware
* Klein (bottle-like functionality)
* Example application
* Form processing middleware?
# GET/POST param middleware factory

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
  for resources, etc.)
