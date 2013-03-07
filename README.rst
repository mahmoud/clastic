clastic
=======

A functional Python web framework that streamlines explicit
development practices while eliminating global state.

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

```
(r'^articles/(?P<year>\d{4})/$', 'news.views.year_archive')
```

And view function:

```
def year_archive(year, month):
    pass
```

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
report`_ for more info.

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
