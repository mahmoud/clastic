# clastic's CHANGELOG

clastic has been used in production web services and microservices
since 2013, and continues to be actively developed and maintained.

Clastic's approach to updates is as follows:

- Prioritize backwards compatibility of public APIs
- Public APIs are those which are documented, or, which are in `__init__` modules.
- [CalVer](https://calver.org) versioning scheme (`YY.MINOR.MICRO`)

Check this page when upgrading to make sure you know about all the new
features and potential breakages.

## 24.0.0

_(Apr 23, 2024)_

- Fix Chameleon support for newer Chameleon versions
- Improved `MetaApplication` support for newer versions of Python (and Windows)

## 23.1.0

_(Dec 17, 2023)_

Dropped Python 2! All dependencies updated accordingly.

## 21.1.2

_(Oct 17, 2023)_

Bumped a few dependencies to their last py2-compatible version ahead of dropping Py3 support in 23.0.0. (Skipped 21.1.1)

## 21.1.0

_(November 7, 2021)_

- Add py3.10 support
- redact secret resources in meta
- fix some py3 meta bugs

Note: Likely last py2/py3 version, pending testing on
[montage](https://github.com/hatnote/montage).

## 21.0.0

_(May 13, 2021)_

Quick compatibility release. Note that future clastic releases will
likely drop Py2.7 support and may drop Werkzeug 1.0 compatibility.

## 20.0.0

_(March 7, 2020)_

- Add support for WSGI middlewares onto clastic's built-in Middleware
- Add RerouteWSGI exception/endpoint function for routing to another wsgi app.
- Better `__str__` on clastic errors
- Fix meta's pyvm component
- Lots of new testing (coverage up to 85%) and fixes
- Refactored BaseRoute/Route into Route/BoundRoute
- Drop Python 3.5 support

  19.0.0

---

_(March 6, 2019)_

First major release, using the CalVer `YY.MINOR.MICRO` scheme. This
release was a huge revamp from past versions, the list of improvements
is long:

## Spotlight

- Python 3 support (3.5+), with 0 warnings
- Werkzeug 0.14.1+ support
- Behind the scenes: Better build matrix, CI, and coverage

## New Features

- `clastic.contrib.objbrowser` revamped and made generally available
  for debugging and exploring the Python memory space
- `clastic.contrib.webtop` now available to all (provided psutil is installed)
- `StatsMiddleware` now uses a Reservoir-per-Route approach for solid
  memory bounding.
- `Application.get_local_client()` for quick access to a local client
  useful for testing.
- `render_basic` now autolinkifies links in docstrings for endpoints
  it renders.
- Generated code is now visible in stack traces (ones which are not
  hidden from the traceback viewer)
- Programmatic version access (`clastic.__version__`)

## Completed Deprecations

- `BaseApplication` merged into `Application`
- `simple_render` etc. now only known as `render_basic`, etc.
- Switch to `boltons.FunctionBuilder` instead of direct `inspect` usage
