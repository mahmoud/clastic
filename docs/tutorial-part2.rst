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
the default behavior of the renderer for nonexisting items is good for now.


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


Now we can read this file as part of our application creation function:

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
       host_url = config["erosion"]["host_url"].rstrip('/') + '/'

       resources = {"host_url": host_url}
       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, resources=resources, render_factory=render_factory)


The application resources are kept as a dictionary.
After getting the host URL from the configuration file,
we put it into this dictionary,
which is then registered with the application during application
instantiation.

Endpoint functions can get application resources
simply by listing them as parameters:

.. code-block:: python

   def home(host_url):
       return {"host_url": host_url}


Let's apply a similar solution for passing the entries to the template.
We will need to store the shortened links in some form of database.
For the sake of simplicity, we'll use the ``shelve`` module
in the Python standard library as our storage backend.
The alias will be the key, and the full link data will be the value.
Here's a simple, initial implementation for the backend,
stored in the file :file:`model.py`:

.. code-block:: python

   import shelve


   class LinkDB:
       def __init__(self, db_path):
           self.db_path = db_path

       def get_links(self):
           with shelve.open(self.db_path) as db:
               entries = list(db.values())
           return entries


Add an option to the configuration file:

.. code-block:: ini

   [erosion]
   host_url = http://localhost:5000
   db_path = erosion.db


Next, add the database connection to the application resources:

.. code-block:: python
   :emphasize-lines: 1, 15, 17

   from model import LinkDB


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
and pass a context to the rendering function.
Below is the implementation
(note that it returns an empty render context for the moment):

.. code-block:: python

   def add_entry(request, db):
       target_url = request.values.get("target_url")
       alias = request.values.get("alias")
       expiry_time = request.values.get("expiry_time")
       max_count = request.values.get("max_count")
       entry = db.add_link(
           target_url=target_url, alias=alias, expiry_time=expiry_time, max_count=max_count
       )
       return {}


We can also see that the endpoint function expects
the storage backend to return the created entry.
The code for storing the link:

.. code-block:: python

   class LinkDB:

       ...

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


The next question is: how do we render this?
We don't want to go to another page,
instead we want to go back to the home page.
Since the home page already lists all entries,
we should be able to see our newly created entry there.
We're going to need a render function
that will redirect the browser to the home page
using the :func:`redirect <clastic.redirect>` function.
Render functions take the context generated by the endpoint function
as their parameter;
although in this case the context is empty
and the render function doesn't do anything with it:

.. code-block:: python

   from clastic import redirect
   from http import HTTPStatus


   def render_add_entry(context):
       return redirect("/", code=HTTPStatus.SEE_OTHER)


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

       config_path = os.path.join(CUR_PATH, "erosion.ini")
       config = ConfigParser()
       config.read(config_path)
       host_url = config["erosion"]["host_url"].rstrip("/") + "/"
       db_path = config["erosion"]["db_path"]

       resources = {"host_url": host_url, "db": LinkDB(db_path)}
       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, resources=resources, render_factory=render_factory)


We add this route as a :func:`POST <clastic.POST>` route.
This makes sure that other HTTP methods will not be allowed for this path.
You can try typing the address ``http://localhost:5000/submit``
into the location bar of your browser,
and you should see a "method not allowed" error.
