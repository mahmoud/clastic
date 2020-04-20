Tutorial (Part 2)
=================


.. note::

   This document continues from where the first part left off.
   As in the first part, we proceed by building on the example application
   step by step.
   It would be helpful to the reader to code along
   and try out the various stages of the application.
   In this manner, completing it should take about an hour.


The first part of the tutorial covered some basic topics
like routing, form handling, static assets, and JSON endpoints.
This second part will cover resource handling, redirection,
and middleware usage.

The example application will be a link shortener.
There will be an option for letting shortened links expire,
based on time or on the number of times they have been clicked.
For the sake of simplicity, we'll use the ``shelve`` module
in the Python standard library as our storage backend.
A stored link entry will consist of the target URL, the (short) alias,
the expiry time, the maximum number of clicks, and the actual number of clicks.
The alias will be the key, and the full link data will be the value.

TODO: more explanation and screenshot


.. contents::
   :local:


Getting started
---------------

Let's jump right in and start with the following application code:

.. code-block:: python

   import os

   from clastic import Application
   from clastic.render import AshesRenderFactory
   from clastic.static import StaticApplication


   CUR_PATH = os.path.dirname(os.path.abspath(__file__))
   STATIC_PATH = os.path.join(CUR_PATH, "static")


   def home():
       return {}


   def create_app():
       static_app = StaticApplication(STATIC_PATH)
       routes = [
           ("/", home, "home.html"),
           ("/static", static_app),
       ]
       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, render_factory=render_factory)


   app = create_app()

   if __name__ == "__main__":
       app.serve()


This is a very simple application that doesn't do anything
that wasn't covered in the first part of the tutorial.
Apart from the static assets, the application has only one route;
and that endpoint doesn't provide any context to the renderer.

And now for the template:

.. code-block:: html

   <!DOCTYPE html>
   <html>
     <head>
       <meta charset="utf-8">
       <title>Erosion</title>
       <link rel="stylesheet" href="/static/style.css">
     </head>
     <body>
       <main class="content">
         <h1>Erosion</h1>
         <p class="tagline">Exogenic linkrot for limited sharing.</p>

         <section class="box">
           <h2>Create a URL</h2>
           <div class="new">
             <form method="POST" action="/submit">
               <p class="target">
                 <label for="target-url">Web URL:</label>
                 <input type="text" id="target-url" name="target_url">
               </p>

               <p>
                 <label for="alias">Shortened as:</label>
                 <span class='input-prefix'>{host_url}</span>
                 <input type="text" id="alias" name="alias">
                 <span class="note">(optional)</span>
               </p>

               <p>
                 <label for="max-count">Click expiration:</label>
                 <input id="max-count" name="max_count" size="3" value="1">
               </p>

               <p>
                 <span class="date-expiry-l">Time expiration:</span>

                 <input type="radio" name="expiry_time" id="after-mins" value="mins">
                 <label for="after-mins" class="date-expiry">five minutes</label>

                 <input type="radio" name="expiry_time" id="after-hour" value="hour" checked>
                 <label for="after-hour" class="date-expiry">one hour</label>

                 <input type="radio" name="expiry_time" id="after-day" value="day">
                 <label for="after-day" class="date-expiry">one day</label>

                 <input type="radio" name="expiry_time" id="after-month" value="month">
                 <label for="after-month" class="date-expiry">one month</label>

                 <input type="radio" name="expiry_time" id="after-none" value="never">
                 <label for="after-none" class="date-expiry">never</label>
               </p>

               <button type="submit">Submit</button>
             </form>
           </div>
         </section>

         {?entries}
         <section>
           <h2>Manage URLs</h2>
           <ul>
             {#entries}
             <li>
               <a href="{host_url}{.alias}">{host_url}{.alias}</a> &raquo; {.target} -
               <span class="click-count"> ({.count} / {.max_count} clicks)</span>
             </li>
             {/entries}
           </ul>
         </section>
         {/entries}
       </main>

       <footer class="content note">
         An example application for
         <a href="https://github.com/mahmoud/clastic">clastic</a>.
       </footer>
     </body>
   </html>


This template consists of two major sections:
one for adding a new entry, and one for managing existing entries.
It expects two items in the render context:

- ``host_url`` for the base URL of the application
- ``entries`` for the shortened links stored in the application

The endpoint provides neither of these but fortunately,
the template engine leaves the parts relating to nonexisting items blank,
which is OK for now.


Resources
---------

The first issue we want to solve is that of passing the host URL
to the template.
To achieve this, we need a way of letting the endpoint function
get the host URL,
so that it can put it into the render context.
Clastic lets us register *resources* with the application;
these will be made available to endpoint functions when requested.

Let's start by adding a simple, ini-style configuration file
named :file:`erosion.ini`,
with the following contents:

.. code-block:: ini

   [erosion]
   host_url = http://localhost:5000


Now we can read this file during application creation:

.. code-block:: python

   def create_app():
       static_app = StaticApplication(STATIC_PATH)
       routes = [
           ("/", home, "home.html"),
           ("/static", static_app),
       ]

       config_path = os.path.join(CUR_PATH, "erosion.ini")
       config = ConfigParser()
       config.read(config_path)

       host_url = config["erosion"]["host_url"].rstrip("/") + "/"
       resources = {"host_url": host_url}

       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, resources=resources, render_factory=render_factory)


The application resources are kept as items in a dictionary
(``resources`` in the example).
After getting the host URL from the configuration file,
we put it into this dictionary,
which then gets registered with the application during application
instantiation.

Endpoint functions can access application resources
simply by listing them (their dictionary keys) as parameters:

.. code-block:: python

   def home(host_url):
       return {"host_url": host_url}


Let's apply a similar solution for passing the entries to the template.
Here's a simple implementation for the storage (file ``storage.py``)
for saving and retrieving link entries:

.. code-block:: python

   import shelve


   class LinkDB:
       def __init__(self, db_path):
           self.db_path = db_path

       def get_links(self):
           with shelve.open(self.db_path) as db:
               entries = list(db.values())
           return entries

       def get_link(self, alias):
           with shelve.open(self.db_path) as db:
               entry = db.get(alias)
           return entry

       def add_link(self, *, target_url, alias, expiry_time, max_count):
           entry = {
               "target": target_url,
               "alias": alias,
               "expiry_time": expiry_time,
               "max_count": max_count,
               "count": 0,
           }
           with shelve.open(self.db_path) as db:
               db[alias] = entry
           return entry


It's worth noting that the ``.add_link()`` method
returns the newly added link.

Now, add an option to the configuration file:

.. code-block:: ini

   [erosion]
   host_url = http://localhost:5000
   db_path = erosion.db


Next, add the database connection to the application resources:

.. code-block:: python
   :emphasize-lines: 1, 16, 17

   from storage import LinkDB


   def create_app():
       static_app = StaticApplication(STATIC_PATH)
       routes = [
           ("/", home, "home.html"),
           ("/static", static_app),
       ]

       config_path = os.path.join(CUR_PATH, "erosion.ini")
       config = ConfigParser()
       config.read(config_path)

       host_url = config["erosion"]["host_url"].rstrip('/') + '/'
       db_path = config["erosion"]["db_path"]
       resources = {"host_url": host_url, "db": LinkDB(db_path)}

       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, resources=resources, render_factory=render_factory)


And finally, use the database resource in the endpoint function:

.. code-block:: python

   def home(host_url, db):
       entries = db.get_links()
       return {"host_url": host_url, "entries": entries}


Redirection
-----------

Let's continue with creating new shortened links.
The new link form submits its data to the ``/submit`` path.
The endpoint function for this path has to receive the data,
add the new entry to the database,
and pass it to the rendering function as part of the context:

.. code-block:: python

   def add_entry(request, db):
       target_url = request.values.get("target_url")
       alias = request.values.get("alias")
       expiry_time = request.values.get("expiry_time")
       max_count = int(request.values.get("max_count"))
       entry = db.add_link(
           target_url=target_url, alias=alias, expiry_time=expiry_time, max_count=max_count
       )
       return {"new_entry": entry}


The next question is: what should the renderer do?
We don't want to display another page, we want to redirect the visitor
back to the home page.
Since the home page lists all entries,
we should be able to see our newly created entry there.
We use the :func:`redirect() <clastic.redirect>` function for this:

.. code-block:: python

   from clastic import redirect
   from http import HTTPStatus


   def render_add_entry(context):
       new_entry = context.get("new_entry")
       return redirect("/", code=HTTPStatus.SEE_OTHER)


Later, we will add a notification to the home page about the newly added link.
And for that, the rendering function gets the new entry
using the special parameter name ``context``
for accessing the render :ref:`context <context-builtin>`.
It doesn't do anything with the entry for now.

What's left is adding this route to the application:

.. code-block:: python
   :emphasize-lines: 1, 8

   from clastic import POST


   def create_app():
       static_app = StaticApplication(STATIC_PATH)
       routes = [
           ("/", home, "home.html"),
           POST("/submit", add_entry, render_add_entry),
           ("/static", static_app),
       ]

       ...


We add this route as a :func:`POST <clastic.POST>` route.
This makes sure that other HTTP methods will not be allowed for this path.
You can try typing the address ``http://localhost:5000/submit``
into the location bar of your browser,
and you should see a "method not allowed" error.
There are also other method-restricted routes,
like :func:`GET <clastic.GET>`, :func:`PUT <clastic.PUT>`, and
:func:`DELETE <clastic.DELETE>`.


Named path segments
-------------------

Now let's turn to using the stored shortened links.
When the shortened link URL is visited,
we just want to redirect the browser to the target URL.
This is going to be a GET-only route:

.. code-block:: python
   :emphasize-lines: 8

   from clastic import GET


   routes = [
       ("/", home, "home.html"),
       POST("/submit", add_entry, render_add_entry, middlewares=[new_link_mw]),
       ("/static", static_app),
       GET('/<alias>', use_entry),
   ]


The "alias" part of the path is placed between angular brackets
to make that segment a named parameter to the endpoint function.
And there is no need for a renderer in this case;
the endpoint function will do the redirection right away:

.. code-block:: python

   def use_entry(alias, db):
       entry = db.get_link(alias)
       return redirect(entry["target"], code=HTTPStatus.MOVED_PERMANENTLY)


Using middleware
----------------

Clastic allows us to use :doc:`middleware <middleware>`
to keep application logic out of endpoint functions and to promote reuse.
For example,
the :class:`PostDataMiddleware <clastic.middleware.form.PostDataMiddleware>`
can be used to convert the form data into appropriate types
and make them available to endpoint functions as parameters:

.. code-block:: python

   from clastic.middleware.form import PostDataMiddleware


   def create_app():
       new_link_mw = PostDataMiddleware(
           {"target_url": str, "alias": str, "max_count": int, "expiry_time": str}
       )

       static_app = StaticApplication(STATIC_PATH)
       routes = [
           ("/", home, "home.html"),
           POST("/submit", add_entry, render_add_entry, middlewares=[new_link_mw]),
           ("/static", static_app),
       ]

       ...


The endpoint function doesn't need to get the data from ``request.values``
anymore:

.. code-block:: python

   def add_entry(db, target_url, alias, expiry_time, max_count):
       entry = db.add_link(
           target_url=target_url, alias=alias, expiry_time=expiry_time, max_count=max_count
       )
       return {}


Cookies
-------

Let's go back to the issue of displaying a notice about newly added links.
At the moment, the ``render_add_entry()`` endpoint function has the data
about the new link,
but redirecting to the home page requires passing that data
over a new HTTP request.
We can use a cookie to achieve this:
the ``render_add_entry()`` function places the data in a cookie,
and the ``home()`` function picks it up from there.

Cookies can be accessed through ``request.cookies``,
but in this example we want to use a signed cookie.
Clastic includes
a :class:`SignedCookieMiddleware <clastic.middleware.cookie.SignedCookieMiddleware>`
for this purpose.
This time we're going to register the middleware at the application level
rather than for just one route.
The secret key for signing the cookie will be read from the configuration file:

.. code-block:: python

   from clastic.middleware.cookie import SignedCookieMiddleware


   def create_app():
       ...

       cookie_secret = config["erosion"]["cookie_secret"]
       cookie_mw = SignedCookieMiddleware(secret_key=cookie_secret)

       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(
           routes,
           resources=resources,
           middlewares=[cookie_mw],
           render_factory=render_factory,
       )


If a function wants to access this cookie,
it just has to declare a parameter named ``cookie``.

Here's how the rendering function stores the new alias in the cookie:

.. code-block:: python

   def render_add_entry(context, cookie):
       new_entry = context.get("new_entry")
       if new_entry is not None:
           cookie["new_entry_alias"] = new_entry["alias"]
       return redirect("/", code=HTTPStatus.SEE_OTHER)


And here's how the endpoint function gets the alias from the cookie,
and puts it into the render context:

.. code-block:: python

   def home(host_url, db, cookie):
       entries = db.get_links()
       new_entry_alias = cookie.pop("new_entry_alias", None)
       return {
           "host_url": host_url,
           "entries": entries,
           "new_entry_alias": new_entry_alias,
       }


And a piece of markup is needed in the template to display the notice:

.. code-block:: html

   <h1>Erosion</h1>
   <p class="tagline">Exogenic linkrot for limited sharing.</p>

   {#new_entry_alias}
   <p>
     Successfully created <a href="{host_url}{.}">{host_url}{.}</a>.
   </p>
   {/new_entry_alias}
