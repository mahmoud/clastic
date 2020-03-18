Errors
======

*Coming soon!*

Errors matter in the HTTP/RESTful ecosystem.

* All Clastic HTTP errors are subtypes of both Response and Exception. Meaning they can be returned or raised, depending on what makes sense for your use case.
* Non-clastic errors which are not handled by your endpoint or middlewares will be handled by the root application's Error Handler. Clastic has at least two built-in, and you can make your own to further customize behavior.


* autodoc
  * All Error types
  * Error handler / contextual error handler
