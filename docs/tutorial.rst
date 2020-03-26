Tutorial
========

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
   and some contain more than two (like "America/North_Dakota/New_Salem".
   Also note that spaces in region and location names are replaced
   with underscores.
   See the `Wikipedia list`_ for more information.


Prerequisites
-------------

First of all, we have to install the dependencies.
These are: *clastic* (obviously) and *dateutil*.
Note that the PyPI package name for *dateutil* is *python-dateutil*::

  pip install clastic python-dateutil



Getting started
---------------

Here is the initial version of our application that only displays
the form but doesn't handle the submitted data:

.. code-block:: python

   import os

   from clastic import Application
   from clastic.render import AshesRenderFactory
   from dateutil import zoneinfo


   def home():
       zone_info = zoneinfo.get_zonefile_instance()
       zone_names = zone_info.zones.keys()
       entries = ((zone.split("/")[-1], zone) for zone in zone_names)
       zones = [
           {"location": location.replace("_", " "), "zone": zone}
           for location, zone in sorted(entries)
       ]
       return {"zones": zones}


   def create_app():
       routes = [("/", home, "home.html")]
       cur_path = os.path.dirname(__file__)
       render_factory = AshesRenderFactory(cur_path)
       return Application(routes, render_factory=render_factory)


   if __name__ == "__main__":
       app = create_app()
       app.serve()


Let's start from the bottom of this code and work our way up:

- In the last ``if`` clause, we create the application
  and start it by invoking its ``.serve()`` method.

- Next, we have the ``create_app()`` function
  where we register the routes of the application.
  A route associates a URL with a function (*endpoint*)
  that will process the requests to that URL.
  In the example, there is only one route where the URL is ``/``
  and the ``home()`` function is the endpoint.

- The route also sets the template file ``home.html``
  to render the response.
  Clastic supports multiple template engines;
  this example uses `ashes`_.
  We create a render factory for rendering templates
  for our chose template engine and tell it where to find
  the template files.

- The application is created by giving the sequence of routes
  and the render factory.

- Finally, the ``home()`` function generates the data
  to be passed to the template.
  The form will contain two dropdown lists for all available time zones,
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
     <form action="." method="post">
       <select name="src">
         {#zones}
         <option value="{zone}">{location}</option>
         {/zones}
       </select>
       <input type="datetime-local" name="dt">
       <select name="dst">
         {#zones}
         <option value="{zone}">{location}</option>
         {/zones}
       </select>
       <button type="submit">Show</button>
     </form>
   </body>
   </html>


Assuming you've named the Python file ``tzconvert.py``,
when you run the command ``python tzconvert.py``,
you can visit the address ``http://127.0.0.1:5000/``
to see the form.


Handling request data
---------------------

Our form submits the data to the current URL,
therefore to the same endpoint.
Now we want to modify the ``home()`` function,
so that if any such data is submitted,
the response page will include the result of the conversion:

.. code-block:: python

   def home(request):
       data = {}
       if "dt" in request.values:
           dt = request.values.get("dt")
           dt_naive = parser.parse(dt)

           src = request.values.get("src")
           data["src_location"] = src.split("/")[-1]

           src_zone = tz.gettz(src)
           src_dt = dt_naive.replace(tzinfo=src_zone)
           data["src_dt"] = src_dt.ctime()

           dst = request.values.get("dst")
           data["dst_location"] = dst.split("/")[-1]

           dst_zone = tz.gettz(dst)
           dst_dt = src_dt.astimezone(dst_zone)
           data["dst_dt"] = dst_dt.ctime()

       zone_info = zoneinfo.get_zonefile_instance()
       zone_names = zone_info.zones.keys()
       entries = ((zone.split("/")[-1], zone) for zone in zone_names)
       zones = [
           {"location": location.replace("_", " "), "zone": zone}
           for location, zone in sorted(entries)
       ]
       data["zones"] = zones
       return data


The changes are that the function now takes ``request`` as a parameter,
and passes extra data to the template
if the request contains a date and time information to convert.
In the template, we add the markup for showing the result:

.. code-block:: html

   <body>
     <h1>Time zone convertor</h1>
     <p class="info">
       When it's {src_dt} in {src_location},<br>
       it's {dst_dt} in {dst_location}.
     </p>
     <form action="." method="post">
       <!-- same as before -->
     </form>
   </body>


.. _Wikipedia list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
.. _ashes: https://github.com/mahmoud/ashes
