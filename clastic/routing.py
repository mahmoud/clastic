# -*- coding: utf-8 -*-

import re
from _errors import (BadRequest,
                     NotFound,
                     MethodNotAllowed,
                     InternalServerError)
from werkzeug.wrappers import BaseResponse


S_REDIRECT = 'redirect'
S_NORMALIZE = 'normalize'
S_STRICT = 'strict'


class RouteMap(object):
    def __init__(self, routes=None, debug=False):
        self._route_list = list(routes or [])
        self.debug = False

    def add(self, route, *args, **kwargs):
        if not isinstance(route, BaseRoute):
            # for when a basic pattern is passed in
            route = BaseRoute(route, *args, **kwargs)
        self._route_list.append(route)

    def dispatch(self, request, slashes=S_NORMALIZE):
        "i know this looks weird, but parsing is always weird, i guess"
        # TODO: Precedence of MethodNotAllowed vs patterns. Do you
        # ever really check the POST of one pattern that much sooner
        # than the GET of the same pattern?

        try:
            return self._dispatch_inner(request, slashes=slashes)
        except Exception as e:
            if self.debug:
                raise
            if isinstance(e, BaseResponse):
                return e
            else:
                #structured traceback, etc.
                return InternalServerError()

    def _dispatch_inner(self, request, slashes=S_NORMALIZE):
        url = request.url
        method = request.method

        _excs = []
        allowed_methods = set()
        for route in self._route_list:
            path_params = route.match_url(url)
            if path_params is None:
                continue
            method_allowed = route.match_method(method)
            if not method_allowed:
                allowed_methods.update(route.methods)
                _excs.append(MethodNotAllowed(allowed_methods))
            injectables = {'_application': self,
                           'request': request,
                           '_route': route}
            injectables.update(path_params)
            injectables.update(self.resources)
            try:
                ep_res = route.execute(**injectables)
            except Exception as e:
                if getattr(e, 'is_breaking', True):
                    raise
                _excs.append(e)
                continue
            return ep_res

        if _excs:
            raise _excs[-1]  # raising the last
        else:
            raise NotFound(is_breaking=False)


BINDING = re.compile(r'<'
                     r'(?P<name>[A-Za-z_]\w*)'
                     r'(?P<op>[?+:*]*)'
                     r'(?P<type>\w+)*'
                     r'>')
TYPE_CONV_MAP = {'int': int,
                 'float': float,
                 'unicode': unicode,
                 'str': unicode}
_path_seg_tmpl = '(?P<%s>(/[\w%%\d])%s)'
_OP_ARITY_MAP = {'': False,  # whether or not an op is "multi"
                 '?': False,
                 ':': False,
                 '+': True,
                 '*': True}


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


class BaseRoute(object):
    def __init__(self, pattern, methods=None):
        self.pattern = pattern
        # TODO: crosscheck methods with known HTTP methods
        self.methods = methods and set([m.upper() for m in methods])
        self.regex, self.converters = self._compile(pattern)

    def match_url(self, url):
        ret = {}
        match = self.regex.match(url)
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

    def _compile(self, pattern):
        processed = []
        var_converter_map = {}

        for part in pattern.split('/'):
            match = BINDING.match(part)
            if not match:
                processed.append(part)
                continue
            parsed = match.groupdict()
            name, type_name, op = parsed['name'], parsed['type'], parsed['op']
            if name in var_converter_map:
                raise ValueError('duplicate path binding %s' % name)
            if op:
                if op == ':':
                    op = ''
                if not type_name:
                    raise ValueError('%s expected a type specifier' % part)
                try:
                    converter = TYPE_CONV_MAP[type_name]
                except KeyError:
                    raise ValueError('unknown type specifier %s' % type_name)
            else:
                converter = unicode

            try:
                multi = _OP_ARITY_MAP[op]
            except KeyError:
                _tmpl = 'unknown arity operator %r, expected one of %r'
                raise ValueError(_tmpl % (op, _OP_ARITY_MAP.keys()))
            var_converter_map[name] = build_converter(converter, multi=multi)

            path_seg_pattern = _path_seg_tmpl % (name, op)
            processed[-1] += path_seg_pattern

        regex = re.compile('/'.join(processed))
        return regex, var_converter_map


def _main():
    rm = RouteMap()
    rp = BaseRoute('/a/b/<t:int>/thing/<das+int>')
    rm.add(rp)
    d = rp.match_url('/a/b/1/thing/1/2/3/4/')
    print d

    d = rp.match_url('/a/b/1/thing/hi/')
    print d

    d = rp.match_url('/a/b/1/thing/')
    print d

    rp = BaseRoute('/a/b/<t:int>/thing/<das*int>', methods=['GET'])
    rm.add(rp)
    d = rp.match_url('/a/b/1/thing/')
    print d
    print list(rm.itermatches('/a/b/1/thing/'))


if __name__ == '__main__':
    _main()




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

"""
