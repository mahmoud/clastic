Tutorial
========

*TODO: add estimated time for reading the document*

In this document, we are going to develop an application
that will convert a given time (and date) between two time zones.
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
for each project,
so we suggest that you create one for this tutorial.
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
It consists of a Python source file (``tzconvert.py``)
and an HTML template file (``home.html``),
both in the same folder.

Here's the Python file:

.. code-block:: python

   import os
   from datetime import datetime

   from clastic import Application
   from clastic.render import AshesRenderFactory
   from dateutil import zoneinfo


   CUR_PATH = os.path.dirname(os.path.abspath(__file__))


   def get_location(zone):
       return zone.split("/")[-1].replace("_", " ")


   def get_all_time_zones():
       zone_info = zoneinfo.get_zonefile_instance()
       zone_names = zone_info.zones.keys()
       entries = {get_location(zone): zone for zone in zone_names}
       return [
           {"location": location, "zone": entries[location]}
           for location in sorted(entries.keys())
       ]


   ALL_TIME_ZONES = get_all_time_zones()


   def home():
       render_ctx = {
           "zones": ALL_TIME_ZONES,
           "default_src": "UTC",
           "default_dst": "UTC",
           "now": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
       }
       return render_ctx


   def create_app():
       routes = [("/", home, "home.html")]
       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, render_factory=render_factory)


   app = create_app()

   if __name__ == "__main__":
       app.serve()


In the last few lines,
we see that this code creates the application
and starts it by invoking its ``.serve()`` method.

Application creation is handled by the ``create_app()`` function,
where we register the routes of the application.
A routing entry associates a route in the application
with a function (*endpoint*) that will process the requests
to that route.
In the example, there is only one entry where the route is ``/``
and the endpoint function is ``home``.

The routing entry also sets the template file ``home.html``
to render the response.
Clastic supports multiple template engines;
in this application we use `Ashes`_.
We create a render factory for rendering templates
for our chosen template engine
and tell it where to find the template files.
Here, we tell the render factory to look for templates
in the same folder as this Python source file.
The application is then created by giving the sequence of routes
and the render factory.

The ``home()`` function generates the data that the template needs
(the "render context").
The form in the template will contain two dropdown lists
for all available time zones,
so we have to pass that list.
Here, we store this data in the ``ALL_TIME_ZONES`` variable
which we have constructed using the ``get_all_time_zones()`` function
as a list of dictionaries
containing the location names
(the last component of the time zone code,
extracted using the ``get_location()`` function),
and the full time zone code.
The location name will be displayed to the user,
whereas the full code will be transmitted as the data.
The entries will be sorted by location name.
We also pass default values for the form inputs:
"UTC" for both the source and destination time zones,
and the current UTC time for the date-time to be converted.


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
       <input type="datetime-local" name="dt" value="{now}" required>

       <div class="timezones">
         <div class="timezone">
           <label for="src">From:</label>
           <select name="src" id="src">
             {#zones}
             {@eq key=location value="{default_src}"}
             <option value="{zone}" selected>{location}</option>
             {:else}
             <option value="{zone}">{location}</option>
             {/eq}
             {/zones}
           </select>
         </div>

         <div class="timezone">
           <label for="dst">To:</label>
           <select name="dst" id="dst">
             {#zones}
             {@eq key=location value="{default_dst}"}
             <option value="{zone}" selected>{location}</option>
             {:else}
             <option value="{zone}">{location}</option>
             {/eq}
             {/zones}
           </select>
         </div>
       </div>

       <button type="submit">Show</button>
     </form>
   </body>
   </html>


With these two files in place, run the command ``python tzconvert.py``
and you can visit the address ``http://127.0.0.1:5000/``
to see the form.


Handling request data
---------------------

The form submits the data to the ``/show`` route,
therefore we need an endpoint function to handle these requests.
First, let's add the corresponding routing entry:

.. code-block:: python

   def create_app():
       routes = [
           ("/", home, "home.html"),
           ("/show", show_time, "show_time.html"),
       ]
       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, render_factory=render_factory)


Next, we'll implement the endpoint function ``show_time()``.
Since this function has to access the submitted data,
it takes the ``request`` as parameter,
and the data in the request is available through ``request.values``.
After calculating the converted time,
it passes the source and destination times to the template,
along with the location names.
Source and destination times consist of dictionary items
indicating how to display them (``text``),
and what data to submit (``value``).

.. code-block:: python

   # from dateutil import parser, tz

   def show_time(request):
       dt = request.values.get("dt")
       dt_naive = parser.parse(dt)

       src = request.values.get("src")
       src_zone = tz.gettz(src)

       dst = request.values.get("dst")
       dst_zone = tz.gettz(dst)

       dst_dt = convert_tz(dt_naive, src_zone, dst_zone)
       render_ctx = {
           "src_dt": {
               "text": dt_naive.ctime(),
               "value": dt
           },
           "dst_dt": {
               "text": dst_dt.ctime(),
               "value": dst_dt.strftime('%Y-%m-%dT%H:%M')
           },
           "src_location": get_location(src),
           "dst_location": get_location(dst),
       }
       return render_ctx


The only missing piece is the ``convert_tz()`` function
that will actually do the conversion:

.. code-block:: python

   def convert_tz(dt_naive, src_zone, dst_zone):
       src_dt = dt_naive.replace(tzinfo=src_zone)
       dst_dt = src_dt.astimezone(dst_zone)
       return dst_dt


And below is a simple ``show_time.html`` template.
Note how the ``text`` and ``value`` subitems are used:

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
       When it's <time datetime="{src_dt.value}">{src_dt.text}</time>
       in {src_location},<br>
       it's <time datetime="{dst_dt.value}">{dst_dt.text}</time>
       in {dst_location}.
     </p>
     <p>Go to the <a href="/">home page</a>.</p>
   </body>
   </html>


Static assets
-------------

As our next step, let us apply some style to our markup.
We create a subfolder named ``static``
in the same folder as our Python source file
and put a file named ``custom.css`` into that folder.
Below is an example content for the file:

.. code-block:: css

   body {
     font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
   }

   h1 {
     font-size: 3em;
     text-align: center;
   }

   form {
     display: flex;
     flex-direction: column;
     align-items: center;
   }

   input, select, button {
     font: inherit;
   }

   label {
     display: block;
   }

   div.timezones {
     display: flex;
     justify-content: space-between;
     margin: 1rem 0;
   }

   div.timezone {
     width: 45%;
   }

   p.info {
     font-size: 2em;
     text-align: center;
     line-height: 2;
   }

   time {
     color: #ff0000;
   }


The changes to the application code will be quite small.
First, we define the path to the folder that contains the static assets:

.. code-block:: python

   CUR_PATH = os.path.dirname(os.path.abspath(__file__))
   STATIC_PATH = os.path.join(CUR_PATH, "static")


And then we add a routing entry
by creating a static application with the static path we have defined,
and we set it as the endpoint that will handle the requests
to any route under ``/static``:

.. code-block:: python

   # from clastic.static import StaticApplication

   def create_app():
       static_app = StaticApplication(STATIC_PATH)
       routes = [
           ("/", home, "home.html"),
           ("/show", show_time, "show_time.html"),
           ("/static", static_app),
       ]
       render_factory = AshesRenderFactory(CUR_PATH)
       return Application(routes, render_factory=render_factory)


Don't forget to add the stylesheet link to the templates:

.. code-block:: html

   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
     <link rel="stylesheet" href="/static/custom.css">
   </head>


.. _list of tz database time zones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
.. _Virtual Environments and Packages: https://docs.python.org/3/tutorial/venv.html
.. _Ashes: https://github.com/mahmoud/ashes
