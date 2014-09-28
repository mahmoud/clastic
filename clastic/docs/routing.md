# Clastic Routing

Much like the main documentation, we'll start with an introduction of
web routing as a fundamental concept and a brief practical
history. Then we'll cover Clastic's approach, highlighting its
simplicity and calling attention to a couple subtleties and powerful
features.

## What is web routing?

In short, an application's routing is the process by which an HTTP
request reaches the logic necessary to fulfill that request. Web
routing is designing predictable systems for configuring and
controlling that process. In this way, web routing is the field of
designing the APIs of web sites, as seen by users and programmatic
clients alike.

## Web routing: A brief history

Routing may seem a small component of a web site or framework, but the
degree of variation between approaches demonstrates just how critical
and confusing a topic it can be. The biggest reason for the diversity
of routing approaches is the power of HTTP. Theoretically speaking, a
framework can route based on any of several dozen HTTP parameters,
including:

* URL path - the first and most common
* Method - GET/HEAD/POST/etc., for the well-RESTed
* Headers - some commonly routed headers include:
  * Accept - based on the mimetype of the requested resource
  * Accept-Language - based on the language of the client
  * Host - the address part of the URL, used for subdomain routing
  * Cookies - and other client-identifying session information
  * User-Agent - trudging through the ever-changing thicket of browsers and clients
  * X-Forwarded-For - de-facto way to handle proxies
* Scheme - such as HTTP or HTTPS

And among these there are subvariations, as well. An important one is
the difference in basic URL routing. One might notice that URL paths,
the part after the address, from the first slash to the end (or first
"?" or "#"), look a lot like directories. Traditionally, URL paths
were treated as directory trees, with leaf nodes being HTML files or
other resources, and the containing directories displaying an index
listing the contents of the directory.

In the last decade or so, however, with the rise of web frameworks,
more and more routing has been done with pattern matching. Regular
expressions on the path and other predicate logic created the "Route"
as a new primitive in web programming, along with the disjoint and
discontinuous site tree. Now, "/item/123" could return a 200 and a
page, while "/item/" returned a 404. By traditional methods, one would
see a landing page, an index of items, or at least a 403 Forbidden on
viewing the index.

## Clastic Web Routing

Clastic's routing system falls under the more modern, predicate-based
routing, and is notable for its simplicity, semantics, and
power. Here's a rundown of Clastic routing features:

1. By default, supports routing based on URL path and HTTP method
2. Route patterns defined with a regex-like syntax to minimize errors
3. Configurable "trailing-slash" behavior (see section below)
4. No automatic reordering of routes (unlike werkzeug)
5. Pluggable error system
6. Middlewares and endpoint functions can participate in routing
7. Deterministic SubApplication embedding

### Route ordering

Web routing in some web frameworks, such as Flask/werkzeug, involves
automatic reordering of an application's routes. Because frequently
this cannot be done unambigiously, reordering is the cause of many
unexpected issues for application developers. In the interest of
predictability and developer control, Clastic keeps Routes in exactly
the order they are passed in.

### Route pattern syntax and definitions

The Route pattern is some string-matching predicate, matched against
the URL Path (the part from the first slash to the end of the URL, or
the first "?" or "#"). Some modern web frameworks, such as Django,
allow patterns to be defined with raw regexes, but this invites errors
to the party. URL paths are not your average strings, and certain
invariants can be enforced to ensure smooth development.

In Clastic, Route patterns are defined with a regex-like syntax that
embraces the semantics of the URL path. Route patterns must begin with
a "/", just like URL paths. Trailing slashes in the pattern denote
whether a route is a branch or leaf (see section on trailing slashes
below). Within the pattern, slashes also have semantic meaning,
delimiting the "segments" of the URL. Segments can be static, such as
"/api/", or dynamically parsed into a value, such as "/<operation>/".

Dynamic segments can be single or multi, and a limited degree of
builtin type matching/parsing is also available. Here are some example
patterns to demonstrate:

1. "/api/<operation>/<args*>"
2. "/add/<numbers*int>"
3. "/delete/<entries+unicode>"
4. "/location/update/<lat:float>/<long:float>"

Some notes:

1. `unicode` is the default type for dynamic path arguments. When type
   is not specified, as with `operation` in example #1, that argument
   will be parsed and injected as unicode.

2. With multisegment arguments, `+` means "one or more" and `*` means
   "zero or more", much like with regular expressions.

3. Multisegment arguments such as `args`, `numbers`, and `entries`, in
   #1, #2, and #3, respectively, will all get those arguments injected as
   lists, with items in the list preparsed into the specified type. If an
   argument fails to parse into the specified type, the route is simply
   not matched.

### HTTP method routing

Clastic also supports routing based on HTTP method. This is done by
either setting the accepted methods on a route or using one of the
convenience classes. This example adds two functionally equivalent
routes to the same application:

  from clastic import Application, Route, GET

  first = GET("/api/find_record", find_record)
  second = Route("/api/find_record", find_record, methods=["GET"])

  app = Application([first, second])

If the path for a given request matches one or more routes' patterns,
but not the accepted HTTP methods, Clastic automatically returns a 405
"Method Not Allowed" HTTP response. This behavior is configurable by
setting an application's RoutingErrorHandler.

### The trailing slash

A single character makes all the difference in a URL. Historically, in
traditional, directory-tree style routing, a trailing slash was often
ignored; a directory is a directory and regardless of slashes, an
index page would be displayed.

Two patterns:

  * "/this/leaf"
  * "/that/branch/"

Based on the presence or absence of the trailing slash, the first
looks like a leaf resource, and the second looks like a branch. Now,
there are four possibilities for clients:

  * "/this/leaf"
  * "/that/branch/"
  * "/this/leaf/"
  * "/that/branch"

The first two exactly match a pattern, and provided everything goes
well in the endpoint, automatically get a 200 response. The second two
access a leaf like a branch and a branch like a leaf,
respectively. Based on the configured slash behavior, the following
can happen:

  * `S_STRICT`, strict slash behavior, returns a 404
  * `S_REWRITE`, internal rewrite behavior, disregards trailing slashes
  * `S_REDIRECT`, redirect response behavior, returns a 30x to the
    correct URL, and is the default

When writing new web applications, `S_REDIRECT` is really the only
option to consider, as it greatly eases writing HTML and manual entry
of addresses. `S_STRICT` may be useful for web APIs and `S_REWRITE` is
probably the least useful, mostly applying to backwards-compatibility
uses.

Route behavior is usually left to the default, `S_REDIRECT`, but
otherwise can be configured at both the Application and Route
level. That is, individual routes can have settings separate from the
application.

### Pluggable exception and edge behavior with RoutingErrorHandler

The RoutingErrorHandler is currently under development so this section
is forthcoming.

### Endpoint and middleware routing participation

By far the most advanced aspect of Clastic routing is the distinction
between "breaking" and "non-breaking" routing exceptions. Imagine a
route matches on the basis of path and method as described above. The
request reaches the endpoint function (aka "controller" in other
frameworks), and determines that for other reasons the route cannot
actually supply an affirmative response to fulfill the request.

At this point the endpoint can raise any number of exceptions, 403
Forbidden and 404 Not Found are common, but in Clastic, it has the
further option of specifying this exception as "non-breaking". A
"non-breaking" exception simply means that this Route cannot fulfill
the request, but it's possible that a Route further down the routing
in the routing priority could.

An example usage of this mechanism is to virtually join two static
directories. A slightly-longer and much more complete version of this
is available under clastic/static.py

  def file_getter(base_dir):
      def get_file(file_path):
          try:
              return FileResponse('/'.join(file_path))
          except FileNotFoundError:
              raise NotFound(is_breaking=False)

   app = Application([('/static/<file_path+>', file_getter('/home/web/static')),
                      ('/static/<file_path+>', file_getter('/home/web/static_old'))])


In the simplified example above, if a client requests
`http://yoursite.com/static/img/friendship.jpg`, and `friendship.jpg`
is not present in `/home/web/static`, the request will fall to the
next matching route, which will search in `/home/web/static_old`. If
`friendship.jpg` is still not found, then the most recent exception, a
404 Not Found, will be returned.

For a very select few, it may be a fun technical aside to think of
web routing as a parsing problem, with Clastic taking a PEG-like
approach, with nonbreaking exceptions enabling restarts.
