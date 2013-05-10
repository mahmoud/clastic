TODO
====

Core
----
* nicer next() names
* polish sub-application mounting
* Sphinx docs
* Pretty 4xx handlers for dev

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
* Document Flaw Application

MetaApplication
---------------
* MetaApplication styling and docs
* IDs
  * Effective uid/gid
  * Saved-set uid/gid
  * Supplementary groups
* Host
  * Some kernel compile/feature flags
  * Processor count
* Process
  * Basic stuff from /proc/self
    * Current mem usage
    * Number of threads
    * Number of open files
  * RSS from pages to bytes
* Python
  * version
  * compile flags
  * runtime flags
* Application
  * Per-route match counters
  * Per-route timing statistics
  * git revision? last update?
* Security
  * Allow bypass for certain IPs
  * Password protection, otherwise

* Group by subapplication? (Allow naming applications)
* Split template into partials, etc.
* P2: better support for child process introspection


## v2
* Custom URL resolvers?
* Failsafe application reloading?
* Middleware <-> middleware merge hook?
* basic checks for URL pattern conflicts?

## Chopping block
* Allowing duplicate middlewares
* endpoint_provides and render_provides

## Curiosities
* dynamic vs. static linked middleware stack performance
* OrderedSets?
* 'strict' mode with more immutability enforcement (immutable dicts
  for resources, etc.) and certain types of linting (detect unset
  global variables)
