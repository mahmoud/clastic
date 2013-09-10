# -*- coding: utf-8 -*-

import re


BINDING = re.compile('\{(?P<name>[A-Za-z_]\w*)(?P<op>[?+:]*)(?P<type>\w+)*\}')
TYPES = {'int': int, 'float': float, 'unicode': unicode, 'str': unicode}
path_component = '(?P<%s>(/[\w%%\d])%s)'


def map_convert(f):
    return lambda value: map(f, (None, value.split('/')))


def safe_convert(f):
    return lambda value: f(value.replace('/', ''))


def compile_route(s):
    processed = []
    converters = {}

    for part in s.split('/'):
        match = BINDING.match(part)
        if not match:
            processed.append(part)
            continue

        parsed = match.groupdict()
        name, type_name = parsed['name'], parsed['type']
        if parsed['op'] == ':':
            if not type_name:
                raise ValueError('%s expected a type specifier' % part)
            parsed['op'] = ''

        converter = TYPES.get(type_name)
        if type_name and not converter:
            raise ValueError('unknown type specifier %s' % type_name)

        if name in converters:
            raise ValueError('duplicate path binding %s' % name)

        if type_name and parsed['op']:
            converters[name] = map_convert(converter)
        else:
            converters[name] = safe_convert(converter)

        processed[-1] += path_component % (name, parsed['op'])

    return '/'.join(processed), converters


def _main():
    raw, converters = compile_route('/a/b/{t:int}/thing/{das+int}')
    print raw
    d = re.match(raw, '/a/b/1/thing/1/2/3/4/').groupdict()
    print d


if __name__ == '__main__':
    _main()
