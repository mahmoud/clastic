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
