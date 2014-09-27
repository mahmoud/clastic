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

* URL, the first and most common
* Method, GET/HEAD/POST/etc., for the well-RESTed
* Headers, some commonly routed headers include:
  * Accept, based on the mimetype of the requested resource
  * Accept-Language, based on the language of the client
  * Host, technically the address part of the URL, used for subdomain routing
  * Cookies, and other client-identifying session information
  * User-Agent, trudging through the ever-changing thicket of browsers and clients
  * X-Forwarded-For, de-facto way to handle proxies
* Scheme, such as HTTP or HTTPS

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

TODO
