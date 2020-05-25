Clastic
=======

.. raw:: html

   <a href="https://pypi.org/project/clastic/"><img src="https://img.shields.io/pypi/v/clastic.svg"></a>
   <a href="https://calver.org/"><img src="https://img.shields.io/badge/calver-YY.MINOR.MICRO-22bfda.svg"></a>

A functional Python web framework that streamlines explicit
development practices while eliminating global state.

Clastic is pure-Python, tested on Python 2.7-3.7, and
`documented <https://python-clastic.readthedocs.io/>`_,
with `tutorials <https://python-clastic.readthedocs.io/en/latest/tutorial.html>`_.

.. contents::
   :depth: 2
   :backlinks: top
   :local:


Quick Start Guide
-----------------

Installation
^^^^^^^^^^^^

Clastic is available `on
PyPI <https://pypi.python.org/pypi/clastic>`_. You can install it by
running this command::

  easy_install clastic

(``pip`` works, too.)


Hello World!
^^^^^^^^^^^^

Getting up and running with Clastic is exceedingly difficult. Just try
and create a file called ``hello.py`` with the following
indecipherable runes:

.. code-block:: python

  from clastic import Application, render_basic

  def hello(name='world'):
      return 'Hello, %s!' % name

  routes = [('/', hello, render_basic),
            ('/<name>', hello, render_basic)]

  app = Application(routes)
  app.serve()

If you run ``python hello.py`` at the command line and visit
http://localhost:5000 in your browser, you will see the text
``Hello, world!``. If instead, you visit http://localhost:5000/Ben
then you will see the text ``Hello, Ben!``. Madness.


Getting fancy with request objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If we add the ``request`` argument to any endpoint function, we get
access to all of the request data, including any GET or POST
parameters or cookies that may have been sent with the request.:

.. code-block:: python

  from clastic import Application, render_basic

  def fancy(request):
      result = ''
      # iterate through all of the GET and POST variables
      for k in request.values:
          result += "Found argument '%s' with value '%s'\n" % (k, request.values[k])
      # iterate through all of the cookies
      for k in request.cookies:
          result += "Found cookie '%s' with value '%s'\n" % (k, request.cookies[k])
      return result

  routes = [('/fancy', fancy, render_basic)]

  app = Application(routes)
  app.serve()

Since we're being fancy, let's create a ``curl`` request which sends a
GET parameter, a POST parameter, and a cookie::

  curl -X POST --data "post=posted" --cookie "cookie_crisp=delicious" --url "http://0.0.0.0:5000/fancy?get=gotten"

In response, Clastic sends the following::

  Found argument 'post' with value 'posted'
  Found argument 'get' with value 'gotten'
  Found cookie 'cookie_crisp' with value 'delicious'

So fancy.

If you're curious how ``request`` got there, read past the end of the
Quickstart.

Pushing the envelope with Response objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the previous examples, we have been returning strings from our
endpoints, letting the trusty ``render_basic`` handle the rest. If
we want more control, then we can remove ``render_basic`` from the
route, opting to instantiate and return our own ``Response`` object
directly.

In the following example, we alter the response headers and status
code to forward the browser back to the main page:

.. code-block:: python

  from clastic import Application, render_basic, Response, redirect

  def home():
      return 'Home, Sweet Home!'

  def return_home():
      response = Response()

      # Forward the client browser to the home page.
      response.headers['Location'] = '/'
      response.status_code = 301

      return response

  def redirect_home():
      return redirect('/')

  routes = [('/', home, render_basic),
            ('/return-home', return_home),
            ('/redirect-home', redirect_home]

  app = Application(routes)
  app.serve()

If you visit the page http://localhost:5000/return-home in your
browser, it will immediately redirect you to the root URL and show the
text ``Home, Sweet Home!``.

The ``Response`` object gives you complete control over all HTTP
headers, enabling you to set and delete cookies, play with page
caching, set page encoding, and so forth. If that sort of fine-grained
responsibility sounds daunting or tedious, you're not alone, which is why
the most common operations usually have convenience functions, like
``redirect()``, which is demonstrated in ``redirect_home()``
above. Clastic also has no-nonsense drop-ins for cookies, HTTP
caching, and more.

Testimonials
------------

While originally built to host `a simple train schedule site
<https://github.com/mahmoud/etavta>`_ and `a few Wikipedia-related
projects <https://github.com/hatnote>`_, Clastic is also used
for both internal and production-grade applications at PayPal.

(If your project or company uses Clastic, feel free to file an issue or
submit a pull request to get added to this section.)

Motivation
----------

Clastic was created to fill the need for a minimalist web framework
that does exactly what you tell it to, while eliminating common
pitfalls and delays in error discovery. The result is a streamlined
and deterministic web development experience.

To put it another way, Clastic is designed such that, by the time your
application has loaded, the framework has done all its work and gotten
out of the way. It doesn't wait until the first request or the first
time a URL is hit to raise an exception.

What is a web application?
--------------------------

In a way, every web framework is a systematic answer to the age-old
question that has baffled humankind until just a few years ago.

.. note::
   The following is a conceptual introduction, not class
   reference. Also, don't be fooled by Capital Letters, Clastic really
   isn't type-heavy.

Request
   A single incoming communication from a client (to your
   application). Encapsulates the WSGI environ, which is just Python's
   representation of an HTTP request.

Response
   An outgoing reply from your application to the client.

A web application exists to accept Requests and produce Responses.
(Clastic knows that every Request has its Response <3)::

  Request --> [Application] --> Response

Route
   A regex-like URL pattern, as associated with an endpoint (and
   optional renderer).

Endpoint
   The function or callable that is called when an incoming
   request matches its associated Route. In Django, this is called a
   *view*, in most MVC frameworks this is called a *controller*.

Renderer
   A function that usually takes a dictionary of values and
   produces a Response. For a typical website, the content of the
   response is usually the result of a templating engine, JSON
   encoder, or file reader.

A web application matches a Request's URL to its Routes' patterns. If
there are no matches, it returns a 404 Response. If a matching Route
is found, the Route's endpoint is called. If it returns a Response or
the Route doesn't have a Renderer, the Response is sent back
directly. Otherwise, the endpoint's return value is fed into the
Renderer, which produces the actual Response::

  Request --> Routes --> Endpoint --> (Renderer) --> Response

.. admonition:: A bit of *context*

   It can be useful to think of an application's behavior in terms of
   overlapping contexts, each with its own lifespan. For instance, a
   logged-in user's session is a context which can span multiple
   requests. A database connection has a context, which may be shorter
   than a Request's context, or longer if your application uses
   connection pooling.

   Application code can introduce dozens of logical contexts, specific
   to its function, but at the Clastic level, there are two primary
   contexts to consider:

   - The Request context, which begins when the Request is constructed
     by the framework, and usually ends when the Response has been
     sent back to the client.
   - The Application context, which begins once an Application is
     successfully constructed at server startup, and ends when the
     server running the Application shuts down.

   Concepts discussed above were more oriented to the Request context,
   the following items are more Application focused.

.. _Resources:

Resources
   A *resource* is a value that is valid for the lifespan of the
   Application. An example might be a database connection factory, a
   logger object, or the path of a configuration file. An
   Application's *resources* refers to a map that gives each resource
   a name.

Render Factory
   A callable which, when called with an argument, returns a suitable
   *renderer*. Consider a ``TemplateRenderFactory``, which, when called
   with the template filename ``index.html``, returns a function that
   can be passed a dictionary to render the application's home page.

   A Render Factory is optional. Here are some cases where a Render Factory can be omitted:

   - an application's endpoints return Responses directly (as many
     applications based directly on Werkzeug do)
   - render functions are specified explicitly on a per-route basis
   - the application is using some fancy middleware to generate
     Responses

Middleware_
   Middleware is a way of splitting up and ordering logic in
   discrete layers. When installed in an Application, Middleware has
   access to the Request before and after the endpoint and render
   steps. In Python itself, decorators could be thought of as a form
   of function middleware.

   There's a lot more to middleware in Clastic, so check out the
   Middleware_ section for more information, including diagrams of
   middleware's role in the request flow.

Armed with this information, it's now possible to define what
constitutes a web application, and indeed a Clastic Application:

Application
   A collection of Resources, list of Routes, and list of Middleware
   instances, with an optional Render Factory to create the rendering
   step for each of the routes.

And with any luck this simple Application should be even simpler:

.. code-block:: python

   resources = {'start_time': time.time()}
   middlewares = [CookieSessionMiddleware()]
   render_factory = TemplateRenderFactory('/path/to/templates/')
   routes = [('/', hello_world, 'home.html')]

   hello_world_app = Application(routes, resources, middlewares, render_factory)

``hello_world_app`` is a full-blown WSGI application ready for serving
to any users needing some greeting.

.. note::
   For the record, the ``Application`` instantiation seen above is exactly
   what is meant by 'constructing' or 'initializing' an
   Application. It's just instantiation, nothing more nothing less.

Dynamic binding
---------------

Dynamic binding, or dynamic *argument* binding, is the process of
resolving the arguments and dependencies of endpoints and middlewares
to produce a rock-solid application. Basically, if a certain endpoint
function takes an argument, Clastic will make sure that argument is
available at Application initialization time.

A simple example
^^^^^^^^^^^^^^^^

Arguments are simply checked by name. Consider the following
"Hello, World!" Application:

.. code-block:: python

  from clastic import Application, render_basic

  def hello(name='world'):
      return 'Hello, %s!' % name

  routes = [('/', hello, render_basic),
            ('/<name>', hello, render_basic)]

  app = Application(routes)
  app.serve()

The ``hello()`` function acts as an endpoint for two Routes, one for
the root URL, and one which takes a ``name`` as a URL path segment. On
visiting the root URL, one sees ``Hello, world!``, and if a ``name`` is
provided, ``Hello, (whatever-was-in-the-URL)``.

If the ``hello()`` function was changed to read:

.. code-block:: python

  def hello(first_name):
      return 'Hello, %s!' % first_name

And the code was run without other changes, an exception would be
raised, originating from line 9, ``app = Application(routes)``::

  NameError: unresolved endpoint middleware arguments: set(['first_name'])

Hmm, looks like we've got a bug, but at least we caught it early. In
the future we should probably use a message bus or maybe Cassandra??
Actually, let's write a quick test:

.. code-block:: python

  def test_hello():
      assert hello() == 'Hello, world!'
      assert hello('Justin') == 'Hello, Justin!'

A nice side-effect of Clastic's argument binding is that endpoints
only take what they need, meaning endpoint functions can have
easy-to-test signatures like ``hello(name)``, instead of
``hello(request, name)``. No need for test clients and mock requests
and other contrivances where unnecessary.

Sources and built-ins
^^^^^^^^^^^^^^^^^^^^^

The "Hello, World!" example used an argument bound in from the URL, one
of the four sources for arguments:

- **Route URL pattern**
- **Application resources** - As `mentioned above`_, arguments which
  are valid for the lifespan of the Application.
- **Middleware provides** - Arguments provided by an Application's
  middleware. See Middleware_ for more information.
- **Clastic built-ins** - Special arguments that are always made
  available by Clastic. These arguments are also reserved, and
  conflicting names will raise an exception. `A list of these arguments
  and their meanings is below.`__

.. _mentioned above: Resources_
__ `List of built-ins`_

List of built-ins
"""""""""""""""""

Clastic provides a small, but powerful set of six built-in arguments
for every occasion. These arguments are reserved by Clastic, so know
them well.

``request``
   Probably the most commonly used built-in, ``request`` is the
   current ``Request`` object being handled by the Application. It has
   the URL arguments, POST parameters, cookies, user agent, other HTTP
   headers, and everything from the WSGI environ.

``next``
   ``next`` is only for use by Middleware, and represents the
   next function in the execution chain. It is called with the
   arguments the middleware class declared that it would provide. If
   the middleware does not provide any arguments, then it is called
   with no arguments.

   ``next`` allows a middleware to not worry about what middleware or
   function comes after it in the chain. All the middleware knows is
   that the result of (or exception raised by) the ``next`` function
   is the Response that a client would receive.

   Middleware functions must accept ``next`` as the first argument. If
   a middleware function does not accept the ``next`` argument, or if
   a non-middleware function accepts the ``next`` argument, an
   exception is raised at Application initialization.

``context``
   ``context`` is the output of the endpoint side of the middleware
   chain. By convention, it is almost always a dictionary of values
   meant to be used in templating or other sorts of Response
   serialization.

   Accepting the ``context`` built-in outside of the render branch of
   middleware will cause an exception to be raised at Application
   initialization.

The following built-ins are considered primarily for internal and
advanced usage, and are thus prefixed with an underscore.

``_application``
   The ``Application`` instance in which this middleware or endpoint
   is currently embedded. The Application has access to all routes,
   endpoints, middlewares, and other fun stuff, which makes
   ``_application`` useful for introspective activities, like those
   provided by Clastic's built-in ``MetaApplication``.

``_route``
   The Route which was matched by the URL and is currently being
   executed. Also mostly introspective in nature. ``_route`` has a lot
   of useful attributes, such as ``endpoint``, which can be used to
   shortcut execution in an extreme case.

And, that's it! All other argument names are unreserved and yours for
the binding.

Constraints
^^^^^^^^^^^

Clastic's dynamic binding system makes for concise, testable web
applications, free of global state and whole classes of common bugs,
but there are a couple implications.

No anonymous arguments
""""""""""""""""""""""

This means that Clastic does not support functions which use ``*args``
or ``**kwargs`` as part of a Route's function chain. In practice, such
signatures reduce testability, introspectability, and debuggability,
while providing little benefit to endpoints and middlewares. As a
result, Clastic actively discourages their use; currently the presence
of such functions does not raise an exception, but this behavior may
change.

There is one substantial exception to this assertion, which is that of
function decorators, which make extensive use of ``*args`` and
``**kwargs``, and of which Clastic is a close cousin. To use
decorators, simply import ``clastic_decorator`` and decorate your
decorator, like so:

.. code-block:: python

  from clastic.decorators import clastic_decorator
  cl_my_deco = clastic_decorator(my_deco)

``clastic_decorator`` simply wraps another decorator in a way that
lifts the eventually decorated function's signature so that it remains
visible to the rest of the Clastic system.

Named URL parameters
""""""""""""""""""""

As a corallary to the above, all parameters in the URL pattern are
required to be named, which in practice, makes for a cleaner and more
testable application. For the few Routes that might actually use such
URLs, simply use a ``path`` converter to capture arbitrarily long
segments and split it in middleware or the endpoint itself.

Naming conflicts
""""""""""""""""

Almost every system has the potential for naming conflicts and Clastic
is no exception. The good news is that Clastic actively checks for
such conflicts at Application initialization. This early-warning
system means naming conflicts are only ever encountered during
development, circumventing the much worse and much more common
scenario of accidental overriding in production.

Because each Route is independent, and there is no global state,
there's no way for one Route's URL parameters to get intermingled with
one another, but it is possible for a URL parameter to conflict with
an Application's resources or middleware-provided arguments. in the
event of such a conflict an error like the following would be raised
at Application initialization::

   NameError: found conflicting provides: [('name', (u'url', u'resources'))]

Which means that ``name`` was provided by both the Route's URL and the
Application's resources.

In practice, Clastic naming conflicts are rare and easily
resolvable. Resolution leads to less ambiguous, more maintainable
code, and the application developer lives to see another day.


Middleware
----------

Middleware can be a very useful way to provide separation of
horizontal concerns from the actual application logic. Common uses
include logging, caching, request serialization/deserialization,
performance profiling, and even compression. Including these functions
in all endpoint functions would be bad design, not to mention a
downright tedious task.

One of Clastic's most defining features may well be its interpretation
of middleware. As opposed to simple pre- and post-request hooks,
Clastic middlewares use real function-nesting scope. Furthermore,
middlewares are dependency-checked to minimize breakage caused by
ordering or accidental omission.

Flow
^^^^

A request flows from the client, to the server, through the
middlewares, to the endpoint/render functions, which produce a
response. The response then travels back through the middlewares, in
reverse order, to the server, which relays it to the client.

Middleware is often described using an onion analogy, wherein the
first middleware gets first say on the request and last say on the
response. For example, given middlewares "A" and "B"::

  --Request--> A --> B --> Endpoint --> B --> A --Response-->

Within each individual middleware class (e.g., "A"), there are three
functions which Clastic will look for and call:

- ``request()`` - most commonly used
- ``endpoint()`` - post-routing, pre-logic
- ``render()`` - post-logic, pre-response, when applicable
  (e.g., template context processing)

Those are terse descriptions, but that's ok, because all you need to
remember is: **"Dial 'M' for Middleware"**::



            (endpoint)   (render)
                |\         /|
                | \       / |
  mw.endpoint() |  \     /  |  mw.render()
                ^   \   /   v
                |    \ /    |
        -- -- --|-- --*-- --|-- -- --
                |           |
  mw.request()  ^           v  mw.request()
                |           |
                |           |
           (Request)     (Response)


To summarize, if a middleware has a ``request`` function, it will be
called such that it wraps both endpoint and render steps, whereas
``endpoint`` and ``render`` functions only wrap their respective
domains. A middleware class can implement all or none of these
functions.

Because Clastic middlewares use nested function scopes, Clastic's
middleware system is essentially a dynamic and specialized decorator
system. Middleware effectively provides hooks for decorating many
endpoints at once.

.. note::

   The ***** at the center vertex of the 'M' represents a checkpoint
   of sorts: If the return value of the endpoint + endpoint
   middlewares is a ``Response`` object, it will be returned directly,
   skipping the ``render`` vertex of the M completely, but still
   executing the outgoing request middlewares.

State
^^^^^

In any framework, all but the simplest middlewares serve some stateful
purpose. Even a simple timer middleware needs to associate a request
with a response to calculate how much time elapsed in between. In
other middleware paradigms, this state usually ends up attached to the
``request`` object, or worse, somewhere in global state:

.. code-block:: python

   class DjangoTimingMiddleware(object):
       # Django-like, might be somewhat simplified

       def process_request(self, request):
           request.start_time = time.time()

       def process_response(self, request, response):
           total_time = time.time() - request.start_time
           return response

       def process_exception(self, request, exception):
           ...  # TODO: exception handling

In Clastic, this would look like:

.. code-block:: python

   class TimingMiddleware(Middleware):
       def request(self, next):
           start_time = time.time()
           try:
               ret = next()
           except:
               raise  # TODO: exception handling
           total_time = time.time() - start_time
           return ret

In this case, local function scope suffices for our calculation, no
need to mutate the request. However, if the middleware did want to
provide something new, it could use the provides system to do so.

Provides
^^^^^^^^

Often, well-intentioned middlewares want to give a little something
back. Clastic let's them do this with *provides*. For an example of
this, here's an ever-so-slightly simplified version of Clastic's basic
built-in cookie session middleware:

.. code-block:: python

    class CookieSessionMiddleware(Middleware):
        provides = ('session',)

        def __init__(self, cookie_name='clastic_session', secret_key=None):
            self.cookie_name = cookie_name
            self.secret_key = secret_key or os.urandom(20)

        def request(self, next, request):
            session = load_cookie(request, self.cookie_name, self.secret_key)
            response = next(session=session)
            session.save_cookie(response, key=self.cookie_name)
            return response

Notice how the ``provides`` class variable, and how the ``next()``
function is called with the ``session`` keyword argument. The endpoint
and nested middlewares now have access to the session, should they
need it, while middlewares before ``CookieSessionMiddleware`` do not.

.. admonition:: Middleware provides vs. resources

   Should a value come from middleware or from the resources? Reading
   the conceptual overview should make this distinction much easier:
   provides are for the lifetime of the *request*, whereas resources
   are for the lifetime of an *application*. A session-store
   connection *factory* is a good resource, but the session retrieved
   is best provided by middleware (if not in the application logic).


Enhancing reusability and testability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Developers using Clastic to its fullest can use middleware to
drastically increase the reusability of their code. Middlewares can be
used to extract variables from the ``request`` and any other complex
objects, then provided to endpoints with much more reusable and
testable usage patterns.

Other frameworks require ``request`` to be passed in as an argument,
even when the endpoint doesn't need it. Still other frameworks provide
``request`` as a threadlocal (thread-**global** anyone?), but this
still makes for harder-to-test code when an endpoint actually does use
a resource provided by request.

Clastic lets you lift nearly anything into a wrapping middleware, so
it's even possible to make Routes that use builtins like ``abs()`` and
``dict()`` as endpoints.


Compared to Django
------------------

Clastic is intentionally much less comprehensive of a web development
suite. Django can be great for beginners or prototypes, and can be
made to work for larger projects, but experienced developers know what
works for them, and Django can get in the way. (Fun Fact:
function-based view deprecation was the straw that led to Clastic)

Here are some Clastic features that might appeal to fellow veteran
Djangonauts:

Proactive URL route checking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For an example of the aggressive checking Clastic provides, consider
the following Django URL route:

.. code-block:: python

   (r'^articles/(?P<year>\d{4})/$', 'news.views.year_archive')

And view function:

.. code-block:: python

    def year_archive(year, month):
        pass

The URL routing rule arguments and view function signature don't
match, but a Django application will happily start up without
complaints, only to 500 on the first access of that URL.

In Clastic, this sort of mismatch will raise an exception when the
Application is constructed.

Better control around application initialization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Django, applications and middleware have no way to detect when they
are fully loaded by the server. Django's lazy loading means middleware
aren't even initialized until the first request. For more information,
see `this Django bug report`_ which led to corrected Django documentation.

.. _this Django bug report:
   https://code.djangoproject.com/ticket/18577

Improved middleware paradigm
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Clastic is all about middleware. Middleware provides modularity with
nesting semantics. Clastic takes the most literal approach to this
possible, using actual function nesting, while Django attempts to
mimic this with a set of hooks. During the context of a request,
middleware calls are not actually nested, and there is no middleware
scope, which usually results in the request object becoming a dumping
ground for middleware context.

There are also certain conditions under which the Django framework
itself may cause an error or reraise an exception in such a way that a
middleware's exception hook is called without having its
process_request hook called. Not only does this make tracking down a
particular bug difficult, but unless middleware is built extremely
conservatively (i.e., assuming nothing; doing an excess of checks),
middleware errors can mask the original exception.

No global state
^^^^^^^^^^^^^^^

Django is beyond dependent on global state. One need look no further
than ``settings.py``; while allegedly modular, Django's ORM and
templating systems cannot be used independently without a settings
module, sometimes an environment variable. Furthermore, it's not
possible or safe to have more than one Django project in one
process. The settings and models would overwrite one another.

This makes Django much less flexible for highly-concurrent or
programmatic usage, but to be fair, other than settings.py filling up
with loggers and other globals, Django's global state isn't the direct
concern of most developers.

That said, Clastic was built 100% free of global state, and provides a
model for application developers to do the same. In addition,
Clastic's model offers some neat functional features, such as
application composability, the ability to embed an application within
another, and dependency checking.

ORM usage
^^^^^^^^^

Django has an ORM. Clastic is ORM-agnostic.

There is an excess of discussion on the pros and cons of ORMs, so
suffice to say that a large portion of experienced engineers find ORM
usage to be detrimental in larger projects. The usual reasoning is
that ORMs make CRUD operations easy, but eventually get in the way of
constructing and tuning more advanced queries.

Portability is a common concern, but very rarely does a real project
switch their RDBMS, if they use relational storage at all. There are
exceptions, but practically speaking, a project runs one of MySQL,
Oracle, or Postgres in production and that or SQLite in
staging/test/local. In fact, for every sizable project that eventually
migrates from MySQL to PostgreSQL, there are at least two which would
benefit from learning and using proprietary features specific to their
chosen database.

Without getting too deep into the dangers of lazy query execution,
let's just say that ORMs, while handy for the short-term and alluring
in the long-term, can make some things appear too easy, resulting in a
template accidentally issuing thousands of queries. It's because of
the obvious nuances that Clastic is not anti-ORM, per se, but doesn't
consider an ORM to be a feature. Every developer has an opinion, and
every project has its needs, so feel free to use Clastic with straight
SQL, SQLAlchemy, your non-relational backend of choice, or even
Django's ORM.

Easier WSGI integration
^^^^^^^^^^^^^^^^^^^^^^^

For as many claims as its docs make to being standard Python, Django
makes `WSGI slightly choreful`_, which is a shame, because `WSGI`_ has
blessed Python with so many neat servers that work with any WSGI
application.

Clastic applications are themselves WSGI applications. There's no need
for special one-off modules or imports.

.. _WSGI slightly choreful:
   https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/

.. _WSGI: http://wsgi.readthedocs.org/en/latest/what.html


Thanks
------

Thanks to the following folks for helping make Clastic:

- `Kurt Rose`_ - Design review and implementation
- `Justin van Winkle`_ - Inspiration
- Pocoo_ and the Werkzeug_ team - For a very great WSGI toolkit

And thanks to *you* for making it this far in the docs!

.. _Kurt Rose: //github.com/doublereedkurt
.. _Justin van Winkle: //twitter.com/jvantastic
.. _Pocoo: //pocoo.org
.. _Werkzeug: //werkzeug.pocoo.org


Misc
----

- `Tarball of Clastic 0.3.0 <https://pypi.python.org/packages/source/c/clastic/clastic-0.3.0.tar.gz#md5=3672ea706921353458fce7714140bde2>`_
