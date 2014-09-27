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

### Route ordering

Web routing in some web frameworks, such as Flask/werkzeug, involves
automatic reordering of an application's routes. Because frequently
this cannot be done unambigiously, reordering is the cause of many
unexpected issues for application developers. In the interest of
predictability and developer control, Clastic keeps Routes in exactly
the order they are passed in.

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
