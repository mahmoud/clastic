Tutorial
========

*TODO: add estimated time for reading the document*

In this document, we are going to develop an application that will
convert a given time (and date) between two time zones.
The user will enter a date and a time,
and select two time zones from a list of all available time zones,
one for the source location and one for the destination location.

.. note::

   Time zones are represented in "region/location" format,
   as in "Australia/Tasmania".
   While most such codes have two components,
   some contain only one (like "UTC"),
   and some contain more than two
   (like "America/North_Dakota/New_Salem").
   Also note that spaces in region and location names are replaced
   with underscores.
   Refer to the `list of tz database time zones`_ for a full list.


Prerequisites
-------------

It's common practice to work in a separate virtual environment
for each project, so we suggest that you create one for this tutorial.
Read the `Virtual Environments and Packages`_ section
of the official Python documentation for more information.

Clastic works with any version of Python.
Let's start by installing it::

  pip install clastic

The example application also makes use of the "dateutil" package.
Note that the PyPI name for that package is *python-dateutil*::

  pip install python-dateutil


Getting started
---------------

The initial version of our application only displays the form,
but doesn't handle the submitted data.
It consists of a Python source file (``tzconvert.py``),
and an HTML template file (``home.html``),
both in the same folder.

Here's the Python file:

.. code-block:: python

   import os

   from clastic import Application
   from clastic.render import AshesRenderFactory
   from dateutil import zoneinfo


   def home():
       render_ctx = {}
       zone_info = zoneinfo.get_zonefile_instance()
       zone_names = zone_info.zones.keys()
       entries = [(zone.split("/")[-1], zone) for zone in zone_names]
       render_ctx["zones"] = [
           {"location": location.replace("_", " "), "zone": zone}
           for location, zone in sorted(entries)
       ]
       return render_ctx


   def create_app():
       routes = [("/", home, "home.html")]
       render_factory = AshesRenderFactory(os.path.dirname(__file__))
       return Application(routes, render_factory=render_factory)


   if __name__ == "__main__":
       app = create_app()
       app.serve()


Let's start from the bottom of this code and work our way up:

- In the last ``if`` clause, we create the application
  and start it by invoking its ``.serve`` method.

- Next, we have the ``create_app`` function
  where we register the routes of the application.
  A routing entry associates a route in the application
  with a function (*endpoint*) that will process the requests
  to that route.
  In the example, there is only one entry where the route is ``/``
  and the endpoint function is ``home``.

- The entry also sets the template file ``home.html``
  to render the response.
  Clastic supports multiple template engines;
  in this application we use `ashes`_.
  We create a render factory for rendering templates
  for our chosen template engine and tell it where to find
  the template files.
  Here, we tell the render factory to look for templates
  in the same folder as this Python source file.

- The application is created by giving the sequence of routes
  and the render factory.

- Finally, the ``home`` function generates the data
  that the template needs.
  The form in the template will contain two dropdown lists
  for all available time zones,
  so we have to pass that list.
  Here, we construct this as a list of dictionaries
  where the keys are the location names
  (the last component of the time zone code),
  and the full time zone code.
  The location name will be displayed to the user,
  whereas the full code will be transmitted as the data.
  The entries will be sorted by location name.


The ``home.html`` template is given below.
In the selection boxes,
for each element in the ``zones`` list that is passed as parameter,
the ``location`` key is used for display
and the ``zone`` key is used for the value:

.. code-block:: html

   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
   </head>
   <body>
     <h1>Time zone convertor</h1>
     <form action="/show" method="post">
       <select name="src">
         {#zones}
         <option value="{zone}">{location}</option>
         {/zones}
       </select>
       <input type="datetime-local" name="dt" required>
       <select name="dst">
         {#zones}
         <option value="{zone}">{location}</option>
         {/zones}
       </select>
       <button type="submit">Show</button>
     </form>
   </body>
   </html>


With these two files in place, run the command ``python tzconvert.py``
and you can visit the address ``http://127.0.0.1:5000/``
to see the form.


Handling request data
---------------------

The form submits the data to the ``/show``,
therefore we need an endpoint function to handle these requests.
First, let's add the corresponding route:

.. code-block:: python

   def create_app():
       routes = [
           ("/", home, "home.html"),
           ("/show", show_time, "show_time.html"),
       ]
       render_factory = AshesRenderFactory(os.path.dirname(__file__))
       return Application(routes, render_factory=render_factory)


Next, we'll implement the endpoint function ``show_time``.
Since this function has to access the submitted data,
it takes the ``request`` as its parameter,
and the data in the request is available through ``request.values``.
After calculating the converted time,
it's going to pass the source and destination times to the template,
along with the location names.

.. code-block:: python

   def show_time(request):
       render_ctx = {}

       dt = request.values.get("dt")
       dt_naive = parser.parse(dt)

       src = request.values.get("src")
       render_ctx["src_location"] = src.split("/")[-1]

       src_zone = tz.gettz(src)
       src_dt = dt_naive.replace(tzinfo=src_zone)
       render_ctx["src_dt"] = src_dt.ctime()

       dst = request.values.get("dst")
       render_ctx["dst_location"] = dst.split("/")[-1]

       dst_zone = tz.gettz(dst)
       dst_dt = src_dt.astimezone(dst_zone)
       render_ctx["dst_dt"] = dst_dt.ctime()

       return render_ctx


And below is a simple ``show_time.html`` template:

.. code-block:: html

   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
   </head>
   <body>
     <h1>Time zone convertor</h1>
     <p class="info">
       When it's {src_dt} in {src_location},<br>
       it's {dst_dt} in {dst_location}.
     </p>
     <p>Go to the <a href="/">home page</a>.</p>
   </body>
   </html>


.. _list of tz database time zones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
.. _Virtual Environments and Packages: https://docs.python.org/3/tutorial/venv.html
.. _ashes: https://github.com/mahmoud/ashes
