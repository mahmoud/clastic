# -*- coding: utf-8 -*-

import re

from .sinter import inject, get_arg_names, getargspec
from .errors import NotFound, MethodNotAllowed
from .middleware import (check_middlewares,
                         merge_middlewares,
                         make_middleware_chain)


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


def collapse_token(text, token=None, sub=None):
    "Collapses whitespace to spaces by default"
    if token is None:
        sub = sub or ' '
        return ' '.join(text.split())
    else:
        sub = sub or token
        return sub.join([s for s in text.split(token) if s])


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
        except KeyError:
            _tmpl = 'unknown arity operator %r, expected one of %r'
            raise InvalidPattern(_tmpl % (op, _OP_ARITY_MAP.keys()))
        var_converter_map[name] = build_converter(cur_conv, multi=multi)

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


class BaseRoute(object):
    def __init__(self, pattern, endpoint=None, methods=None, **kwargs):
        self.slash_mode = kwargs.pop('slash_mode', S_REDIRECT)
        if kwargs:
            raise TypeError('unexpected keyword args: %r' % kwargs.keys())
        self.pattern = pattern
        self.endpoint = endpoint
        self._execute = endpoint
        self.methods = methods and set([m.upper() for m in methods])
        self._compile()

    def _compile(self):
        # maybe: if not getattr(self, 'regex', None) or \
        #          self.regex.pattern != self.pattern:
        self.regex, self.converters = _compile_path_pattern(self.pattern,
                                                            self.slash_mode)
        self.path_args = self.converters.keys()
        if self.methods:
            unknown_methods = list(self.methods - HTTP_METHODS)
            if unknown_methods:
                raise InvalidMethod('unrecognized HTTP method(s): %r'
                                    % unknown_methods)
            if 'GET' in self.methods:
                self.methods.add('HEAD')

    @property
    def is_branch(self):
        return self.pattern.endswith('/')

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

    def execute(self, request, **kwargs):
        if not self._execute:
            raise InvalidEndpoint('no endpoint function set on %r' % self)
        kwargs['_route'] = self
        kwargs['request'] = request
        return inject(self._execute, kwargs)

    def iter_routes(self):
        yield self

    def bind(self, application, *a, **kw):
        "BaseRoutes do not bind, but normal Routes do."
        return

    def __repr__(self):
        cn = self.__class__.__name__
        ep = self.endpoint
        try:
            ep_name = '%s.%s' % (ep.__module__, ep.func_name)
        except:
            ep_name = repr(ep)
        args = (cn, self.pattern, ep_name)
        tmpl = '<%s pattern=%r endpoint=%s>'
        if self.methods:
            tmpl = '<%s pattern=%r endpoint=%s methods=%r>'
            args += (self.methods,)
        return tmpl % args


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


class Route(BaseRoute):
    def __init__(self, pattern, endpoint, render=None,
                 render_error=None, **kwargs):
        self._middlewares = list(kwargs.pop('middlewares', []))
        self._resources = dict(kwargs.pop('resources', []))
        super(Route, self).__init__(pattern, endpoint, **kwargs)

        self._bound_apps = []
        self.endpoint_args = get_arg_names(endpoint)

        self._execute = None
        self._render = None
        self._render_factory = None
        self.render_arg = render
        if callable(self.render_arg):
            self._render = self.render_arg
        self._render_error = render_error

    def execute(self, request, **kwargs):
        injectables = {'_route': self,
                       'request': request,
                       '_application': self._bound_apps[-1]}
        injectables.update(self._resources)
        injectables.update(kwargs)
        return inject(self._execute, injectables)

    def render_error(self, request, _error, **kwargs):
        if not callable(self._render_error):
            raise TypeError('render_error not set or not callable')
        injectables = {'_route': self,
                       '_error': _error,
                       'request': request,
                       '_application': self._bound_apps[-1]}
        injectables.update(self._resources)
        injectables.update(kwargs)
        return inject(self._render_error, injectables)

    def empty(self):
        # more like a copy
        self_type = type(self)
        ret = self_type(self.pattern, self.endpoint, self.render_arg)
        ret.__dict__.update(self.__dict__)
        ret._middlewares = list(self._middlewares)
        ret._resources = dict(self._resources)
        ret._bound_apps = list(self._bound_apps)
        return ret

    def bind(self, app, **kwargs):
        rebind_render = kwargs.pop('rebind_render', True)
        inherit_slashes = kwargs.pop('inherit_slashes', True)
        rebind_render_error = kwargs.pop('rebind_render_error', True)
        if kwargs:
            raise TypeError('unexpected keyword args: %r' % kwargs.keys())

        resources = getattr(app, 'resources', {})
        middlewares = getattr(app, 'middlewares', [])
        if rebind_render:
            render_factory = getattr(app, 'render_factory', None)
        else:
            render_factory = self._render_factory
        if rebind_render_error:
            render_error = getattr(app.error_handler, 'render_error', None)
        else:
            render_error = self._render_error

        merged_mw = merge_middlewares(self._middlewares, middlewares)

        params = {'app': app,
                  'resources': dict(self._resources, **resources),
                  'middlewares': merged_mw,
                  'render_factory': render_factory,
                  'render_error': render_error}

        # test a copy of the route before making any changes, for extra safety
        r_copy = self.empty()
        if inherit_slashes:
            r_copy.slash_mode = app.slash_mode
        r_copy._bind_args(**params)
        r_copy._compile()
        # if none of the above raised an exception, we're golden

        if inherit_slashes:
            self.slash_mode = app.slash_mode
        self._bind_args(**params)
        self._compile()
        self._bound_apps += (app,)
        return self

    def _bind_args(self, app, resources, middlewares,
                   render_factory, render_error):
        url_args = set(self.converters.keys())
        builtin_args = set(RESERVED_ARGS)
        resource_args = set(resources.keys())

        tmp_avail_args = {'url': url_args,
                          'builtins': builtin_args,
                          'resources': resource_args}
        check_middlewares(middlewares, tmp_avail_args)
        provided = resource_args | builtin_args | url_args
        if callable(render_factory) and self.render_arg is not None \
                and not callable(self.render_arg):
            _render = render_factory(self.render_arg)
        elif callable(self._render):
            _render = self._render
        else:
            _render = _noop_render
        _execute = make_middleware_chain(middlewares, self.endpoint, _render, provided)

        if callable(render_error):
            check_render_error(render_error, resources)

        self._resources.update(resources)
        self._middlewares = middlewares
        self._render_factory = render_factory
        self._render = _render
        self._render_error = render_error
        self._execute = _execute

    def get_info(self):
        ret = {}
        route = self
        ep_args, _, _, ep_defaults = getargspec(route.endpoint)
        ep_defaults = dict(reversed(zip(reversed(ep_args),
                                        reversed(ep_defaults or []))))
        ret['url_pattern'] = route.pattern
        ret['endpoint'] = route.endpoint
        ret['endpoint_args'] = ep_args
        ret['endpoint_defaults'] = ep_defaults
        ret['render_arg'] = route.render_arg
        srcs = {}
        for arg in route.endpoint_args:
            if arg in RESERVED_ARGS:
                srcs[arg] = 'builtin'
            elif arg in route.arguments:
                srcs[arg] = 'url'
            elif arg in ep_defaults:
                srcs[arg] = 'default'
            for mw in route._middlewares:
                if arg in mw.provides:
                    srcs[arg] = mw
            if arg in route._resources:
                srcs[arg] = 'resources'
            # TODO: trace to application if middleware/resource
        ret['sources'] = srcs
        return ret


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
        super(NullRoute, self).bind(*a, **kw)


#
#  Convenience classes for common HTTP methods
#

class GET(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('GET',)
        super(GET, self).__init__(*a, **kw)


class POST(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('POST',)
        super(POST, self).__init__(*a, **kw)


class PUT(Route):
    def __init__(self, *a, **kw):
        kw['methods'] = ('PUT',)
        super(PUT, self).__init__(*a, **kw)


class DELETE(Route):
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
