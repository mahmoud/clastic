# -*- coding: utf-8 -*-

import re


BINDING = re.compile(r'\<(?P<name>[A-Za-z_]\w*)(?P<op>[?+:]*)(?P<type>\w+)*\>')
TYPES = {'int': int, 'float': float, 'unicode': unicode, 'str': unicode}
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


class RoutePattern(object):
    def __init__(self, pattern):
        self.pattern = pattern
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
        except KeyError:
            return None  # TODO
        except (TypeError, ValueError):
            return None
        return ret

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
                    converter = TYPES[type_name]
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
    rp = RoutePattern('/a/b/<t:int>/thing/<das+int>')
    d = rp.match_url('/a/b/1/thing/1/2/3/4/')
    print d

    d = rp.match_url('/a/b/1/thing/hi/')
    print d


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

Since Werkzeug's constraining of syntax led to a better system,
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

"""
