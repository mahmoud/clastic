Troubleshooting
===============

*TODO* (should this be "Best Practices" or similar?)

Building web applications is never as easy as it seems.
Luckily, clastic was built with debuggability in mind.

Flaw
----

If you're using the built-in dev server, by default it reloads the
application when you save a file that's part of the
application. If you accidentally save a typo, Clastic will boot
up a failsafe application on the same port and show you a stack
trace to help you track down the error.
Save again, and your application should come back up.

Debug Mode
----------

By default, when running the built-in dev server, Clastic exposes `werkzeug's debug application <https://werkzeug.palletsprojects.com/en/1.0.x/debug/>`_.

Project structure
-----------------

*TODO*

* app.py
  * create_app() function
  * app = ...
