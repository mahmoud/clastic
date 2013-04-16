# TODO
======

Core
----
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
* Freshen up debugger
  * Hide interstitial frames
* Lighter-weight static content route/middleware/application
* Document flaw

MetaApplication
---------------
* Process start time + pid
* Parent process start time + ppid
* System load
* Application start time
* Per-route match counters
* List of middleware, resources, etc.
* Group by subapplication? (Allow naming applications)



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
