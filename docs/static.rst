Static
======

All web applications consist of a mix of technologies.
Most human-facing websites serve up JavaScript, CSS, and HTML.

Some of these files make sense to generate dynamically, others
can be served from a file on the filesystem. Here is where
Clastic's static serving facilities shine.

* StaticFileRoute
  * For when you have a single file at a single path
  * Will check for existence of file at startup by default, to be safe
* StaticApplication
  * For when you have a directory

Advanced static serving
-----------------------

* StaticApplications can overlap in paths, and if the first
  Application can't locate the requested resource, the second
  Application will try, and so on. This makes it easy to serve
  multiple directories' files from the same URL path.
