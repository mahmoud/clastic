Breaking changes in Clastic 0.4
===============================

This file lists some of the potentially breaking changes in Clastic
0.4.0, for the (temporary) reference of Clastic users. If there are
any questions, feel free to reach out with a Github issue.

* URL pattern syntax overhaul
* URLs internally rewritten by default, not redirected
* Route.rule -> Route.pattern
* Route.arguments -> Route.path_args (path_arguments is a bit long)
* Application(routes, resources, render_factory <-> middlewares)
* clastic.core split into clastic.routing, clastic.application
* All new error system, does not inherit from Werkzeug's HTTPException
  (does inherit from Werkzeug's Response though)
