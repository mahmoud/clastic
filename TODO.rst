TODO
====

Core
----
* nicer next() names
* polish sub-application mounting
* Sphinx docs
* Pretty 4xx handlers for dev
* Make MetaApplication instantiatable
* Make render functions more like middlewares (to unify return/raise branching and facilitate format-multiplexed renderers)
* Give render_factories a chance to return something for None inputs
* `context` is way too general of a name for the return of the endpoint

Contrib
-------
* Secure sessions
* Cache middleware
* Form processing middleware?
* Freshen up debugger
  * Hide interstitial frames
* Document Flaw Application
* Memory referrents app

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


* handle Flaw issue in '''Application([('/one/two', lambda one, two: int(one) + int(two), default_response)]).serve()'''
