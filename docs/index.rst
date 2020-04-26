.. Clastic documentation master file, created by
   sphinx-quickstart on Tue Mar 17 23:21:21 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Clastic
=======

|release| |calver| |changelog|

**Clastic** is a Pythonic microframework for building web applications featuring:

* Fast, coherent routing system
* Powerful middleware architecture
* Built-in observability features via the ``meta`` Application
* Extensible support for multiple templating systems
* Werkzeug_-based WSGI/HTTP primitives, same as Flask_

.. _Werkzeug: https://github.com/pallets/werkzeug
.. _Flask: https://github.com/pallets/flask

Installation
------------

Clastic is pure Python, and tested on Python 2.7-3.7+, as well as PyPy. Installation is easy::

  pip install clastic

Then get to building your first application!

.. code-block:: python

  from clastic import Application, render_basic

  app = Application(routes=[('/', lambda: 'hello world!', render_basic)])

  app.serve()
  # Visit localhost:5000 in your browser to see the result!

Getting Started
---------------

Check out our :doc:`Tutorial <tutorial>` for more.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tutorial
   tutorial-part2
   application
   middleware
   errors
   meta_application
   static
   troubleshooting
   compared

.. |release| image:: https://img.shields.io/pypi/v/clastic.svg
             :target: https://pypi.org/project/clastic/

.. |calver| image:: https://img.shields.io/badge/calver-YY.MINOR.MICRO-22bfda.svg
            :target: https://calver.org

.. |changelog| image:: https://img.shields.io/badge/CHANGELOG-UPDATED-b84ad6.svg
            :target: https://github.com/mahmoud/clastic/blob/master/CHANGELOG.md
