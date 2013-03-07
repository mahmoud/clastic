clastic
=======

A functional Python web framework that streamlines explicit
development practices while eliminating global state.

.. contents::
   :depth: 2
   :backlinks: top
   :local:


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
   `view`, in most MVC frameworks this is called a `controller`.

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

   A Render Factory is optional

Middleware_
   Middleware is a way of splitting up and ordering logic in
   discrete layers. When installed in an Application, Middleware has
   access to the Request before and after the endpoint and render
   steps. In Python itself, decorators could be thought of as a form
   of function middleware. There's a lot more to middleware in
   Clastic, so check out the Middleware_ section for more information.

Armed with this information, it's now possible to define what
constitutes a web application, and indeed a Clastic Application:

Application
   A collection of Resources, list of Routes, and list of Middleware
   instances, with an optional Render Factory to create the rendering
   step for each of the routes.

And with any luck this simple Application should be even simpler::

   resources = {'start_time': time.time()}
   middlewares = [CookieSessionMiddleware()]
   render_factory = TemplateRenderFactory('/path/to/templates/')
   routes = [('/', hello_world, 'home.html')]

   hello_world_app = Application(routes, resources, render_factory, middlewares)

``hello_world_app`` is a full-blown WSGI application ready for serving
to any users needing some greeting.

.. note::
   For the record, the ``Application`` instantiation seen above is exactly
   what is meant by 'constructing' or 'initializing' an
   Application. It's just instantiation, nothing more nothing less.


Middleware
----------

Middleware can be a very useful way to provide separation of
horizontal concerns from the actual application logic. Common uses
include logging, caching, request serialization/deserialization,
performance profiling, and even compression, Including these functions
in all endpoints would be bad design, not to mention downright
tedious.

Clastic's most defining feature may well be its interpretation of
middleware. As opposed to simple pre- and post- request hooks, Clastic
middlewares use real function-nesting scope. Furthermore, are
dependency-checked to minimize breakage caused by ordering or
accidental omission.

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
 - ``endpoint()`` - kind of meh, but good to be complete
 - ``render()`` - useful for context processing

Those are terse descriptions, but that's ok, because all you need to
remember is: **"'M' for Middleware"**::



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

   The ***** at the middle vertex of the 'M' represents a checkpoint
   of sorts. If the return value of the endpoint + endpoint
   middlewares is a ``Response`` object, it will be returned
   directly, skipping the ``render`` side of the M completely.

State
^^^^^

In any framework, all but the simplest middlewares serve some stateful
purpose. Even a simple timer middleware needs to associate a request
with a response to calculate how much time elapsed in between. In
other middleware paradigms, this state usually ends up attached to the
``request`` object, or worse, somewhere in global state::

   class DjangoTimingMiddleware(object):
       # Django-like, might be somewhat simplified

       def process_request(self, request):
           request.start_time = time.time()

       def process_response(self, request, response):
           total_time = time.time() - request.start_time
           return response

       def process_exception(self, request, exception):
           ...  # TODO: exception handling

In Clastic, this would look like::

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
built-in cookie session middleware::

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
the following Django URL route::

   (r'^articles/(?P<year>\d{4})/$', 'news.views.year_archive')

And view function::

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
aren't even initialized until the first request. See `this Django bug
report`_ for more information.

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
blessed Python has so many neat servers that work with any WSGI
application.

Clastic applications are themselves WSGI applications. There's no need
for special one-off modules or imports.

.. _WSGI slightly choreful:
   https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/

.. _WSGI: http://wsgi.readthedocs.org/en/latest/what.html
