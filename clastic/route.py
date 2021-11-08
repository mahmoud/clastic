# -*- coding: utf-8 -*-

import re

from boltons.iterutils import first

from .sinter import inject, get_arg_names, get_fb, get_callable_name
from .middleware import (check_middlewares,
                         merge_middlewares,
                         make_middleware_chain)
try:
    unicode = unicode
except NameError:
    # py3
    unicode = str


_REQUEST_BUILTINS = ('request', '_application', '_route', '_dispatch_state')
_RENDER_BUILTINS = _REQUEST_BUILTINS + ('context',)
RESERVED_ARGS = _RENDER_BUILTINS + ('next',)


class InvalidEndpoint(ValueError):
    pass


class InvalidPattern(ValueError):
    pass


class InvalidMethod(ValueError):
    pass


HTTP_METHODS = set(['GET', 'HEAD', 'POST', 'PUT', 'DELETE',
                    'OPTIONS', 'TRACE', 'CONNECT', 'PATCH'])


S_REDIRECT = 'redirect'  # return a 30x to the right URL
S_REWRITE = 'rewrite'    # perform a rewrite (like an internal redirect)
S_STRICT = 'strict'      # return a 404, get it right or go home


BINDING = re.compile(r'<'
                     r'(?P<name>[A-Za-z_]\w*)'
                     r'(?P<op>\W*)'
                     r'(?P<type>\w+)*'
                     r'>')

_FLOAT_PATTERN = r'[+-]?\ *(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?'
_INT_PATTERN = r'[+-]?\ *[0-9]+'
_STR_PATTERN = r'[^/]+'

_SEG_TMPL = '(?P<{name}>({sep}{pattern}){arity})'
_PATH_SEG_TMPL = '(?P<%s>(/[^/]+)%s)'
_OP_ARITY_MAP = {'': False,  # whether or not an op is "multi"
                 '?': False,
                 ':': False,
                 '+': True,
                 '*': True}

_OP_OPTIONALITY_MAP = {'': False,  # whether or not an op is "optional"
                       '?': True,
                       ':': False,
                       '+': False,
                       '*': True}


TYPE_CONV_MAP = {}
TYPE_PATT_MAP = {}
DEFAULT_CONVS = [('int', int, _INT_PATTERN),
                 ('float', float, _FLOAT_PATTERN),
                 ('str', unicode, _STR_PATTERN),
                 ('unicode', unicode, _STR_PATTERN)]


def _register_converter(name, func, pattern):
    """
    This is here for completeness, but usage is discouraged. Anything
    more complex than a basic/builtin type should be converted in a
    Middleware or in the endpoint function.
    """
    global TYPE_CONV_MAP, TYPE_PATT_MAP
    TYPE_CONV_MAP[name] = func
    TYPE_PATT_MAP[name] = pattern


for name, func, pattern in DEFAULT_CONVS:
    _register_converter(name, func, pattern)


def build_converter(converter, optional=False, multi=False):
    if multi:
        def multi_converter(value):
            if not value and optional:
                return []
            return [converter(v) for v in value.split('/')[1:]]
        return multi_converter

    def single_converter(value):
        if not value and optional:
            return None
        return converter(value.replace('/', ''))
    return single_converter


def _compile_path_pattern(pattern, mode=S_REWRITE):
    processed = []
    var_converter_map = {}

    if not pattern.startswith('/'):
        raise InvalidPattern('URL path patterns must start with a forward'
                             ' slash (got %r)' % pattern)
    if '//' in pattern:
        raise InvalidPattern('URL path patterns must not contain multiple'
                             'contiguous slashes (got %r)' % pattern)
    sep = '/+'
    if mode == S_STRICT:
        sep = '/'
    for part in pattern.split('/'):
        match = BINDING.match(part)
        if not match:
            processed.append(part)
            continue
        parsed = match.groupdict()
        name, type_name, op = parsed['name'], parsed['type'], parsed['op']
        if name in var_converter_map:
            raise InvalidPattern('duplicate path binding %s' % name)
        if op == ':':
            op = ''
        if not type_name:
            type_name = 'unicode'
        try:
            cur_conv = TYPE_CONV_MAP[type_name]
            cur_patt = TYPE_PATT_MAP[type_name]
        except KeyError:
            raise InvalidPattern('unknown type specifier %s'
                                 % type_name)
        try:
            multi = _OP_ARITY_MAP[op]
            optional = _OP_OPTIONALITY_MAP[op]
        except KeyError:
            _tmpl = 'unknown arity operator %r, expected one of %r'
            raise InvalidPattern(_tmpl % (op, _OP_ARITY_MAP.keys()))
        var_converter_map[name] = build_converter(cur_conv,
                                                  multi=multi,
                                                  optional=optional)
        path_seg_pattern = _SEG_TMPL.format(name=name,
                                            sep=sep,
                                            pattern=cur_patt,
                                            arity=op)
        processed[-1] += path_seg_pattern
    full_pattern = '^'
    if mode != S_STRICT and not processed[-1]:
        processed = processed[:-1]
    full_pattern += sep.join(processed)
    if mode != S_STRICT:
        full_pattern += '/*'
    regex = re.compile(full_pattern + '$')
    return regex, var_converter_map


def normalize_path(path, is_branch):
    ret = [x for x in path.split('/') if x]
    if not ret:
        return '/'
    ret = [''] + ret
    if is_branch:
        ret.append('')
    return '/'.join(ret)


def _noop_render(context):
    return context


def check_render_error(render_error, resources):
    re_avail_args = set(_REQUEST_BUILTINS) | set(resources)
    re_avail_args.add('_error')

    re_args = set(get_arg_names(render_error))
    missing_args = sorted(re_args - re_avail_args)
    if missing_args:
        raise NameError('unresolved render_error() arguments: %r'
                        % missing_args)
    return True


class BoundRoute(object):
    def __init__(self, route, app, **kwargs):
        # TODO: maybe two constructors, one for initial binding, one for rebinding?

        # keep a reference to the unbound version
        self.unbound_route = unbound_route = getattr(route, 'unbound_route', route)
        self.bound_apps = getattr(route, 'bound_apps', []) + [app]

        prefix = kwargs.pop('prefix', '')
        rebind_render = kwargs.pop('rebind_render', True)
        inherit_slashes = kwargs.pop('inherit_slashes', True)
        rebind_render_error = kwargs.pop('rebind_render_error', True)
        if kwargs:
            raise TypeError('unexpected keyword args: %r' % kwargs.keys())

        self.pattern = prefix + route.pattern
        self.slash_mode = app.slash_mode if inherit_slashes else route.slash_mode
        self.methods = route.methods

        self.regex, self.converters = _compile_path_pattern(self.pattern,
                                                            self.slash_mode)
        self.path_args = self.converters.keys()
        self.endpoint_args = get_arg_names(unbound_route.endpoint)

        app_resources = getattr(app, 'resources', {})
        self.resources = dict(app_resources)
        self.resources.update(getattr(route, 'resources', {}))
        app_mws = getattr(app, 'middlewares', [])
        self.middlewares = tuple(merge_middlewares(getattr(route, 'middlewares', []), app_mws))

        # rebind_render=True is basically a way of making the
        # generated render function sticky to the most-recently bound
        # application which can fulfill it.
        bind_render = rebind_render or route.render is _noop_render or not callable(route.render)

        render_factory_list = [getattr(ba, 'render_factory', None) for ba in self.bound_apps]
        render_factory = first(reversed(render_factory_list), key=callable)

        if callable(unbound_route.render):
            # explicit callable renders always take precedence
            render = unbound_route.render
            render_factory = None
        elif bind_render and render_factory and unbound_route.render is not None:
            render = render_factory(unbound_route.render)
        else:
            # default to carrying through values from the route
            render = route.render if callable(route.render) else _noop_render
            render_factory = getattr(route, 'render_factory', None)
        self.render_factory = render_factory
        self.render = render

        if rebind_render_error:
            render_error = getattr(app.error_handler, 'render_error', None)
        else:
            render_error = route.render_error
        if callable(render_error):
            check_render_error(render_error, self.resources)
        self.render_error = render_error

        src_provides_map = {'url': set(self.converters),
                            'builtins': set(RESERVED_ARGS),
                            'resources': set(self.resources)}
        check_middlewares(self.middlewares, src_provides_map)
        provided = set.union(*src_provides_map.values())

        self._execute = make_middleware_chain(self.middlewares, unbound_route.endpoint, render, provided)

        self._required_args = self._resolve_required_args()

    def bind(self, app, **kwargs):
        return BoundRoute(self, app, **kwargs)

    def iter_routes(self):
        yield self

    @property
    def endpoint(self):
        return self.unbound_route.endpoint

    @property
    def is_branch(self):
        return self.unbound_route.is_branch

    @property
    def render_arg(self):
        return self.unbound_route.render

    def match_path(self, path):
        ret = {}
        match = self.regex.match(path)
        if not match:
            return None
        groups = match.groupdict()
        try:
            for conv_name, conv in self.converters.items():
                ret[conv_name] = conv(groups[conv_name])
        except (KeyError, TypeError, ValueError):
            return None
        return ret

    def match_method(self, method):
        if method and self.methods:
            if method.upper() not in self.methods:
                return False
        return True

    def _resolve_required_args(self, with_builtins=False):
        """Creates a list of fully resolved endpoint requirements, working
        backwards from the arguments in the endpoint function
        signature.

        Underlying functions have checks for cycles, etc., but most of
        those issues will be caught before this resolution
        happens. For instance, this method will not raise an error if
        no middleware provides a certain argument. That check and many
        others are done at bind time by make_middleware_chain.
        """
        args = {}

        def add(provides):
            for p in provides:
                args.setdefault(p, [])

        def add_func(provides, func=None):
            func = func or (lambda: None)  # convenience for unset mw methods
            fb = get_fb(func)
            deps = fb.args
            defaulted_deps = fb.get_defaults_dict()

            # XXX: at this point are there cases where provides can conflict?
            for p in provides:
                args.setdefault(p, []).extend(deps)

            for ddep in defaulted_deps:
                # if the ddep is already present, another source is
                # providing it and the signature default won't be used
                if ddep not in args:
                    args[ddep] = []
            return

        url_args = self.converters.keys()
        add(url_args)
        add(RESERVED_ARGS)
        add(self.resources.keys())

        for mw in self.middlewares:
            add_func(mw.provides, mw.request)
            add_func(mw.endpoint_provides, mw.endpoint)
            add_func(mw.render_provides, mw.render)

        add_func(['__endpoint_response__'], self.unbound_route.endpoint)

        resolved = resolve_deps(args)

        ret = resolved['__endpoint_response__']
        if not with_builtins:
            ret = [d for d in ret if d not in RESERVED_ARGS]

        return ret

    def get_required_args(self):
        return list(self._required_args)

    def is_required_arg(self, arg_name):
        return arg_name in self._required_args

    def execute(self, request, **kwargs):
        injectables = {'_route': self,
                       'request': request,
                       '_application': self.bound_apps[-1]}
        injectables.update(self.resources)
        injectables.update(kwargs)
        return inject(self._execute, injectables)

    def execute_error(self, request, _error, **kwargs):
        if not callable(self.render_error):
            raise TypeError('render_error not set or not callable')
        injectables = {'_route': self,
                       '_error': _error,
                       'request': request,
                       '_application': self.bound_apps[-1]}
        injectables.update(self.resources)
        injectables.update(kwargs)
        return inject(self.render_error, injectables)

    def __repr__(self):
        cn = self.__class__.__name__
        return '<%s route=%r bound_app=%r>' % (cn, self.unbound_route, self.bound_apps[-1])


class Route(object):
    """While Clastic may revolve around the :class:`Application`,
    Applications would be nothing without the Routes they contain.

    The :class:`Route` object is basically a combination of three things:

      1. A path *pattern*
      2. An *endpoint* function
      3. A *render* function or argument

    Put simply, when a request matches a Route's *pattern*,
    Clastic calls the Route's *endpoint* function, and the result of
    this is passed to the Route's *render* function.

    In reality, a Route has many other levers to enable more routing features.

    Args:

      pattern (str): A :ref:`pattern-minilanguage`-formatted string.
      endpoint (callable): A function to call with :ref:`injectables`,
        which returns a Response or a render context which will be
        passed to the Route's *render* function.
      render (callable): An optional function which converts the output of
        *endpoint* into a Response. Can also be an argument which is
        passed to an Application's render_factory to generate a render
        function. For instance, a template name or path.
      middlewares (list): An optional list of middlewares specific to this Route.
      resources (dict): An optional dict of resources specific to this Route.
      methods (list): A list of text names of `HTTP methods
        <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods>`_
        which a request's method must match for this Route to match.
      render_error (callable): *Advanced*: A function which converts
        an :exc:`HTTPException` into a Response. Defaults to the
        Application's :ref:`error handler <error-handlers>`.
    """
    def __init__(self, pattern, endpoint, render=None,
                 render_error=None, **kwargs):
        self.middlewares = list(kwargs.pop('middlewares', []))
        self.resources = dict(kwargs.pop('resources', []))

        self.slash_mode = kwargs.pop('slash_mode', S_REDIRECT)
        methods = kwargs.pop('methods', None)

        if kwargs:
            raise TypeError('unexpected keyword args: %r' % kwargs.keys())

        self.methods = methods and set([m.upper() for m in methods])
        if self.methods:
            unknown_methods = list(self.methods - HTTP_METHODS)
            if unknown_methods:
                raise InvalidMethod('unrecognized HTTP method(s): %r'
                                    % unknown_methods)
            if 'GET' in self.methods:
                self.methods.add('HEAD')

        _compile_path_pattern(pattern, self.slash_mode)  # checking pattern
        self.pattern = pattern

        if not callable(endpoint):
            raise TypeError('expected endpoint to be a function or method, not: %r' % endpoint)
        self.endpoint = endpoint
        self.render_error = render_error
        if callable(render_error):
            check_render_error(render_error, self.resources)
        self.render = render

    @property
    def is_branch(self):
        return self.pattern.endswith('/')

    def iter_routes(self):
        yield self

    def bind(self, app, **kwargs):
        return BoundRoute(self, app, **kwargs)

    def __repr__(self):
        cn = self.__class__.__name__
        ep = self.endpoint
        try:
            ep_mod, ep_name = get_callable_name(ep)
            ep_name = '%s.%s' % (ep.__module__, ep.func_name)
        except Exception:
            ep_name = object.__repr__(ep)
        args = (cn, self.pattern, ep_name)
        tmpl = '<%s pattern=%r endpoint=%s>'
        if self.methods:
            tmpl = '<%s pattern=%r endpoint=%s methods=%r>'
            args += (self.methods,)
        return tmpl % args


class NullRoute(Route):
    def __init__(self, *a, **kw):
        super(NullRoute, self).__init__('/<_ignored*>',
                                        self.handle_sentinel_condition,
                                        slash_mode=S_REWRITE)

    def handle_sentinel_condition(self, request,
                                  _application, _route, _dispatch_state):
        err_handler = _application.error_handler
        if _dispatch_state.exceptions:
            return _dispatch_state.exceptions[-1]
        elif _dispatch_state.allowed_methods:
            MNAType = err_handler.method_not_allowed_type
            return MNAType(allowed_methods=_dispatch_state.allowed_methods)
        else:
            NFType = err_handler.not_found_type
            return NFType(dispatch_state=_dispatch_state,
                          request=request,
                          application=_application)

    def bind(self, *a, **kw):
        kw['inherit_slashes'] = False
        return super(NullRoute, self).bind(*a, **kw)


def resolve_deps(dep_map):
    # TODO: keyfunc

    # first, make a clean copy
    dep_map = normalize_deps(dep_map)

    # second, check for cycles
    cycle = find_cycle(dep_map, prenormalize=False)
    if cycle:
        links_str = ', '.join(['%r->%r' % (t, d) for t, d
                               in zip(cycle, cycle[1:])])
        raise RuntimeError('cycle detected (%s)' % links_str)

    dict_type = type(dep_map)
    resolved_map = dict_type([(k, []) for k in dep_map])

    for cur_target, cur_resolved_deps in resolved_map.items():
        cur_deps = list(reversed(dep_map[cur_target]))
        while cur_deps:
            cd = cur_deps.pop()
            if cd not in cur_resolved_deps:
                cur_resolved_deps.append(cd)
            cd_deps = dep_map.get(cd, [])
            cur_deps.extend(reversed(cd_deps))

    return resolved_map


def normalize_deps(dep_map):
    """Returns a copy of *dep_map* with no duplicate dependencies for a
    given target, and all dependencies properly represented as targets.
    """
    ret = type(dep_map)()  # work with dict/OrderedDict/etc.

    for k, _deps in dep_map.items():
        cur_seen = set()
        ret[k] = []
        for d in _deps:
            if d not in ret:
                ret[d] = []
            if d in cur_seen:
                continue
            ret[k].append(d)
            cur_seen.add(d)

    return ret


def find_cycle(dep_map, prenormalize=True):
    """Returns the first cycle it finds, or None if there aren't any.

    Normalizes first, but if the dep_map is already normalized, save
    some time with prenormalize=False.

    This implementation is based off of a Guido + Norvig collab, oddly
    enough.
    """
    if prenormalize:
        dep_map = normalize_deps(dep_map)
    rem_nodes = list(dep_map.keys())
    while rem_nodes:
        cur_root = rem_nodes.pop()
        cur_path = [cur_root]
        while cur_path:
            cur_deps = list(dep_map[cur_path[-1]])
            while cur_deps:
                cd = cur_deps.pop()
                if cd in cur_path:
                    return cur_path + [cd]
                if cd in rem_nodes:
                    cur_path.append(cd)
                    rem_nodes.remove(cd)
                    break
            else:
                cur_path.pop()
    return None


#
#  Convenience classes for common HTTP methods
#

class GET(Route):
    """A :class:`Route` subtype which only matches for GET requests."""

    def __init__(self, *a, **kw):
        kw['methods'] = ('GET',)
        super(GET, self).__init__(*a, **kw)


class POST(Route):
    "A :class:`Route` subtype which only matches for POST requests."
    def __init__(self, *a, **kw):
        kw['methods'] = ('POST',)
        super(POST, self).__init__(*a, **kw)


class PUT(Route):
    "A :class:`Route` subtype which only matches for PUT requests."
    def __init__(self, *a, **kw):
        kw['methods'] = ('PUT',)
        super(PUT, self).__init__(*a, **kw)


class DELETE(Route):
    "A :class:`Route` subtype which only matches for DELETE requests."
    def __init__(self, *a, **kw):
        kw['methods'] = ('DELETE',)
        super(DELETE, self).__init__(*a, **kw)


#
#  Boutique HTTP methods (for consistency)
#

class HEAD(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('HEAD',)
        super(HEAD, self).__init__(*a, **kw)


class OPTIONS(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('OPTIONS',)
        super(OPTIONS, self).__init__(*a, **kw)


class TRACE(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('TRACE',)
        super(TRACE, self).__init__(*a, **kw)


class CONNECT(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('CONNECT',)
        super(CONNECT, self).__init__(*a, **kw)


class PATCH(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('PATCH',)
        super(PATCH, self).__init__(*a, **kw)

"""
Routing notes
-------------

After being betrayed by Werkzeug routing in too many fashions, and
after reviewing many designs, a new routing scheme has been designed.

Clastic's existing pattern (inherited from Werkzeug) does have some
nice things going for it. Django routes with regexes, which can be
semantically confusing, bug-prone, and unspecialized for
URLs. Clastic/Werkzeug offer a constrained syntax/grammar that is
specialized to URL pattern generation. It aims to be:

 * Clear
 * Correct
 * Validatable

The last item is of course the most important. (Lookin at you Werkzeug.)

Werkzeug's constraints on syntax led to a better system, so
Clastic's routing took it a step further. Take a look at some examples:

 1. '/about/'
 2. '/blog/{post_id?int}'
 3. '/api/{service}/{path+}'
 4. '/polish_maths/{operation:str}/{numbers+float}'

1. Static patterns work as expected.

2. The '?' indicates "zero or one", like regex. The post_id will be
converted to an integer. Invalid or missing values yield a value of
None into the 0-or-1 binding.

3. Bindings are of type 'str' (i.e., string/text/unicode object) by
default, so here we have a single-segment, string 'service'
binding. We also accept a 'path' binding. '+' means 1-or-more, and the
type is string.

4. Here we do some Polish-notation math. The operation comes
first. Using an explicit 'str' is ok. Numbers is a repeating path of
floats.


Besides correctness, there are a couple improvements over
Werkzeug. The system does not mix type and arity (Werkzeug's "path"
converter was special because it consumed more than one path
segment). There are just a few built-in converters, for the
convenience of easy type conversion, not full-blown validation. It's
always confusing to get a vague 404 when better error messages could
have been produced (there are middlewares available for this).

(Also, in Werkzeug I found the commonly-used '<path:path>' to be
confusing. Which is the variable, which is the converter? {path+} is
better ;))


# TODO: should slashes be optional? _shouldn't they_?
# TODO: detect invalid URL pattern
# TODO: ugly corollary? unicode characters. (maybe)
# TODO: optional segments shouldn't appear anywhere but the tail of the URL
# TODO: slash redirect stuff (bunch of twiddling necessary to get
# absolute path for Location header)

# TODO: could methods be specified in the leading bit of the pattern?
# probably getting too fancy

"""

"""
Recently chopped "error handler" logic executed on uncaught exceptions
(within the except block in dispatch())::

                code = getattr(e, 'code', None)
                if code in self.error_handlers:
                    handler = self.error_handlers[code]
                else:
                    handler = self.error_handlers.get(None)

                if handler:
                    err_injectables = {'error': e,
                                       'request': request,
                                       '_application': self}
                    return inject(handler, err_injectables)
                else:
                    if code and callable(getattr(e, 'get_response', None)):
                        return e.get_response(request)
                    else:
                        raise

The reason this logic was not very clasticky was mostly because it was
purely Application-oriented, not Route-oriented, and did not translate
well on re-embeds/SubApplication usage.

Some form of error_render or errback should come into existence at
some point, but design is pending.

##############

RouteList -> Like a SubApplication but holds unbound routes, along
with certain directions for when they are bound. I.e.,

* rebind renders
* rebind error renders
* inherit slash mode behavior
"""
