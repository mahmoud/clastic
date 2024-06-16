Tutorial: Time zone convertor
=============================

.. note::

   This document starts out with a fairly simple application code
   and proceeds by building on it.
   Therefore, we recommend that the reader codes along
   and tries out the various stages of the application.
   In this manner, completing it should take about an hour.

While Clastic supports building all sorts of web applications and services,
our first project will be a traditional, HTML-driven web application.
It will convert a given time (and date) between two time zones.
The user will enter a date and time,
and select two time zones from a list of all available time zones,
one for the source location and one for the destination location.
A screenshot of the final application is shown below.

.. figure:: images/tzconvert_screenshot.*
   :alt: Application screenshot showing the user selected time
     in Tijuana and Timbuktu.
   :align: center

   After selecting the time and two time zones,
   clicking the "Show" button will display
   the given time in the source location
   and the corresponding time in the destination location.

Before we start, a note about time zones:
these are represented in "region/location" format, as in "Africa/Timbuktu".
While most such codes have two parts, some have only one (like "UTC"),
and some have more than two (like "America/North_Dakota/New_Salem").
Also note that spaces in region and location names are replaced
with underscores.
Refer to the "`List of tz database time zones`_" for a full list.


.. contents::
   :local:


Prerequisites
-------------

It's common practice to work in a separate virtual environment
for each project,
so we suggest that you create one for this tutorial.
Read the "`Virtual Environments and Packages`_" section
of the official Python documentation for more information.

For this application, the only prerequisite is installing Clastic::

  pip install clastic

.. note::

   We are going to use the ``zoneinfo`` module
   which was added to the standard library in Python version 3.9.
   If it's not available in your environment,
   you can adjust the code to use the `dateutil`_ package.


Getting started
---------------

Our first implementation will just display the form;
it won't handle the submitted data.
It consists of a Python source file and an HTML template file,
both in the same folder.

First, let's take a look at the template file (``home.html``):


.. code-block:: html
   :linenos:

   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
   </head>
   <body>
     <h1>Time zone convertor</h1>
     <form action="/show" method="POST">
       <input type="datetime-local" name="dt" value="{default_time}" required>

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

.. note::

   Clastic supports multiple template engines;
   in this application we use `Ashes`_.
   Ashes is a Python implementation of the `Dust`_ template engine
   for JavaScript.

This template expects some data to be passed to it.
These are marked using curly brackets:

- ``default_time`` on line 10: The default time.
- ``default_src`` on line 17: The default source time zone.
- ``default_dst`` on line 30: The default destination time zone.
- ``zones`` on lines 16 and 29: A list of all available time zones,
  where each element is a dictionary in the form::

    {"location": "LOCATION", "zone": "REGION/LOCATION"}

  For each option in the selection box,
  the value of the  ``location`` key is displayed to the user,
  and the value of the ``zone`` key is submitted as the data
  (lines 18, 20, 31, 33).

Note that the form is submitted to the ``/show`` address (action on line 9)
which we will introduce later.

Next, we turn to the Python code (``tzconvert.py``):


.. code-block:: python
   :linenos:

   from datetime import datetime, timezone
   from pathlib import Path
   from zoneinfo import available_timezones

   from clastic import Application
   from clastic.render import AshesRenderFactory


   def get_location(zone):
       return zone.split("/")[-1].replace("_", " ")


   def get_all_time_zones():
       time_zones = []
       for zone in available_timezones():
           entry = {
               "location": get_location(zone),
               "zone": zone,
           }
           time_zones.append(entry)
       return sorted(time_zones, key=lambda x: x["location"])


   ALL_TIME_ZONES = get_all_time_zones()


   def home():
       render_ctx = {
           "zones": ALL_TIME_ZONES,
           "default_src": "UTC",
           "default_dst": "UTC",
           "default_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
       }
       return render_ctx


   def create_app():
       routes = [
           ("/", home, "home.html"),
       ]
       templates_path = Path(__file__).parent
       render_factory = AshesRenderFactory(str(templates_path))
       return Application(routes, render_factory=render_factory)


   app = create_app()

   if __name__ == "__main__":
       app.serve()


Let's go through this code piece by piece,
starting at the bottom and working our way up.

In the last few lines, we create the application and start it
by invoking its :meth:`~clastic.Application.serve` method:


.. code-block:: python

   app = create_app()

   if __name__ == "__main__":
       app.serve()


We create the application in the ``create_app()`` function,
where we register the routes of the application.
Every :class:`~clastic.Route` associates a path
with a function (*endpoint*) that will process the requests to that path.
In the example, there is only one route where the path is ``/``
and the endpoint function is ``home``:


.. code-block:: python

   def create_app():
       routes = [
           ("/", home, "home.html"),
       ]
       templates_path = Path(__file__).parent
       render_factory = AshesRenderFactory(str(templates_path))
       return Application(routes, render_factory=render_factory)


The route sets the template file ``home.html`` to render the response.
We create a render factory for rendering templates
for our chosen template engine
(in this case, an :class:`~clastic.render.AshesRenderFactory`)
and tell it where to find the template files.
Here, we tell the render factory to look for templates
in the same folder as this Python source file.
The :class:`~clastic.Application` is then created
by providing the routes and the render factory.

The ``home()`` function generates the data that the template expects
(called the "*render context*").
The default time is the current time in the UTC time zone;
the default for both the source and destination time zones is UTC;
and the zones list is stored in the ``ALL_TIME_ZONES`` variable:


.. code-block:: python

   def home():
       render_ctx = {
           "default_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
           "default_src": "UTC",
           "default_dst": "UTC",
           "zones": ALL_TIME_ZONES,
       }
       return render_ctx


The list of all time zones is constructed once, at application startup:


.. code-block:: python

   def get_location(zone):
       return zone.split("/")[-1].replace("_", " ")


   def get_all_time_zones():
       time_zones = []
       for zone in available_timezones():
           entry = {
               "location": get_location(zone),
               "zone": zone,
           }
           time_zones.append(entry)
       return sorted(time_zones, key=lambda x: x["location"])


   ALL_TIME_ZONES = get_all_time_zones()


With these two files in place, run the command ``python tzconvert.py``,
and you can visit the address ``http://localhost:5000/`` to see the form.


Handling request data
---------------------

Our application submits the form data to another page
(the ``/show`` path), but that page doesn't exist yet.
Again, we start with the template (``show_time.html``):


.. code-block:: html
   :linenos:

   <!DOCTYPE html>
   <html lang="en">
   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
   </head>
   <body>
     <h1>Time zone convertor</h1>
     <p>
       When it's <time datetime="{src_dt.value}">{src_dt.text}</time>
       in {src_location},<br>
       it's <time datetime="{dst_dt.value}">{dst_dt.text}</time>
       in {dst_location}.
     </p>
     <p>Go to the <a href="/">home page</a>.</p>
   </body>
   </html>


The render context for this template has to contain variables
for the source and destination locations
(``src_location`` and ``dst_location``),
and variables for the source and destination date and times
(``src_dt`` and ``dst_dt``).
The date and time variables should be dictionaries
with the keys ``text`` and ``value``,
where ``text`` is the textual representation to display to the user,
and ``value`` is the technical representation suitable for processing.

In the Python code, we need an endpoint function to handle these requests.
First, let's add the corresponding route:


.. code-block:: python
   :emphasize-lines: 4

   def create_app():
       routes = [
           ("/", home, "home.html"),
           ("/show", show_time, "show_time.html"),
       ]
       templates_path = Path(__file__).parent
       render_factory = AshesRenderFactory(str(templates_path))
       return Application(routes, render_factory=render_factory)


Next, we implement the endpoint function ``show_time()``.
Since this function has to access the submitted data,
it takes the :ref:`request-builtin` as parameter,
and the data in the request is available through ``request.values``.
After calculating the converted time,
the function passes the source and destination times to the template,
along with the location names.


.. code-block:: python

   from zoneinfo import ZoneInfo


   def show_time(request):
       dt = request.values.get("dt")
       dt_naive = datetime.strptime(dt, "%Y-%m-%dT%H:%M")

       src = request.values.get("src")
       src_zone = ZoneInfo(src)

       dst = request.values.get("dst")
       dst_zone = ZoneInfo(dst)

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


Static assets
-------------

As our next step, let us apply some style to our page.
Adding styles will require a CSS file, which should be served without processing.
Such files are generally known as *static assets*.
We create a subfolder named ``static``
in the same folder as our Python source file
and put a file named ``custom.css`` into that folder.
Here's a minimal example content for the file:


.. code-block:: css

   body {
     font-family: system-ui, sans-serif;
   }

   label {
     display: block;
   }

   div.timezones {
     display: flex;
     gap: 1rem;
     margin-block: 1rem;
   }

   time {
     color: red;
   }


The changes to the Python code will be quite small.
We just add a route by creating a :class:`~clastic.static.StaticApplication`
with the file system path to the folder containing the static assets,
and we set it as the endpoint that will handle any requests
to paths under ``/static``:

.. code-block:: python
   :emphasize-lines: 5, 6, 10

   from clastic.static import StaticApplication


   def create_app():
       static_path = Path(__file__).parent / "static"
       static_app = StaticApplication(str(static_path))
       routes = [
           ("/", home, "home.html"),
           ("/show", show_time, "show_time.html"),
           ("/static", static_app),
       ]
       templates_path = Path(__file__).parent
       render_factory = AshesRenderFactory(str(templates_path))
       return Application(routes, render_factory=render_factory)


Don't forget to add the stylesheet link to both template files:


.. code-block:: html
   :emphasize-lines: 4

   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
     <link rel="stylesheet" href="/static/custom.css">
   </head>


Working with JSON
-----------------

Our last task is to display the converted time
on the same page as the form instead of moving to a second page.
In order to achieve this,
we're going to implement a basic JSON API endpoint
to update the page with data sent to and received from the application.

Actually, we can use our existing ``show_time()`` function for this purpose.
Instead of applying an HTML template to the render context dictionary
returned by this function,
we can pass it to the :func:`~clastic.render_json` function
to generate a JSON response.

.. code-block:: python
   :emphasize-lines: 9

   from clastic import render_json


   def create_app():
       static_path = Path(__file__).parent / "static"
       static_app = StaticApplication(str(static_path))
       routes = [
           ("/", home, "home.html"),
           ("/show", show_time, render_json),
           ("/static", static_app),
       ]
       templates_path = Path(__file__).parent
       render_factory = AshesRenderFactory(str(templates_path))
       return Application(routes, render_factory=render_factory)


At this point, you should be able to test this route using `curl`_::

  $ curl -X POST -d dt='2024-06-15T21:39' -d src='America/Tijuana' -d dst='Africa/Timbuktu' http://localhost:5000/show
  {
    "dst_dt": {
      "text": "Sun Jun 16 04:39:00 2024",
      "value": "2024-06-16T04:39"
    },
    "dst_location": "Timbuktu",
    "src_dt": {
      "text": "Sat Jun 15 21:39:00 2024",
      "value": "2024-06-15T21:39"
    },
    "src_location": "Tijuana"
  }

Now we arrange the home page template.
First, we add a modal dialog to display the result.
By default, it contains placeholder values:


.. code-block:: html

   ...
   </form>

   <dialog id="result">
     <p>
       When it's <time id="src_dt" datetime="2024-01-01T18:00">Jan 1 2024</time>
       in <span id="src_location">UTC</span>,<br>
       it's <time id="dst_dt" datetime="2024-01-01T18:00">Jan 1 2024</time>
       in <span id="dst_location">UTC</span>.
     </p>
   </dialog>


We add a static file named ``static/show_time.js`` that contains
our JavaScript code:


.. code-block:: JavaScript
   :linenos:

   async function showResult(event, form) {
       event.preventDefault();
       const response = await fetch(form.action, {
           method: "POST",
           body: new FormData(form),
       });
       const json = await response.json();
       document.getElementById("src_dt").innerHTML = json["src_dt"]["text"];
       document.getElementById("src_dt").setAttribute("datetime", json["src_dt"]["value"]);
       document.getElementById("src_location").innerHTML = json["src_location"];
       document.getElementById("dst_dt").innerHTML = json["dst_dt"]["text"];
       document.getElementById("dst_dt").setAttribute("datetime", json["dst_dt"]["value"]);
       document.getElementById("dst_location").innerHTML = json["dst_location"];
       document.getElementById("result").showModal();
   }


This function gets the converted time from the JSON endpoint (lines 3-7),
updates the data in the modal (lines 8-13),
and brings up the modal (line 14).

Finally, we have to add the script to the home page
and call the ``showResult`` function when the submit button is pressed:


.. code-block:: html
   :emphasize-lines: 5, 9

   <head>
     <meta charset="utf-8">
     <title>Time zone convertor</title>
     <link rel="stylesheet" href="/static/custom.css">
     <script src="/static/show_time.js"></script>
   </head>
   <body>
     <h1>Time zone convertor</h1>
     <form action="/show" method="POST" onsubmit="showResult(event, this)">


Conclusion
----------

This concludes the introductory tutorial.
The full application code can be found in the `repo`_.
Check out the :doc:`second part <tutorial-part2>`
to learn more about Clastic's features.


.. _List of tz database time zones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
.. _Virtual Environments and Packages: https://docs.python.org/3/tutorial/venv.html
.. _dateutil: https://dateutil.readthedocs.io/
.. _Ashes: https://github.com/mahmoud/ashes
.. _Dust: https://akdubya.github.io/dustjs/
.. _curl: https://curl.haxx.se/
.. _repo: https://github.com/mahmoud/clastic/tree/master/examples/tzconvert
