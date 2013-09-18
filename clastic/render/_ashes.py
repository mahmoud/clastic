# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import cgi
import json
import urllib
import codecs

import sys
PY3 = (sys.version_info[0] == 3)
if PY3:
    unicode, basestring = str, str

__version__ = '0.5.3'
__author__ = 'Mahmoud Hashemi'
__contact__ = 'mahmoudrhashemi@gmail.com'
__url__ = 'https://github.com/mahmoud/ashes'
__license__ = 'BSD'


# need to add group for literals
# switch to using word boundary for params section
node_re = re.compile(r'({'
                     r'(?P<closing>\/)?'
                     r'(?:(?P<symbol>[\~\#\?\@\:\<\>\+\^\%])\s*)?'
                     r'(?P<refpath>[a-zA-Z0-9_\$\.]+|"[^"]+")'
                     r'(?:\:(?P<contpath>[a-zA-Z0-9\$\.]+))?'
                     r'(?P<filters>\|[a-z]+)*?'
                     r'(?P<params>(?:\s+\w+\=(("[^"]*?")|([\w\.]+)))*)?'
                     r'\s*'
                     r'(?P<selfclosing>\/)?'
                     r'\})',
                     flags=re.MULTILINE)

key_re_str = '[a-zA-Z_$][0-9a-zA-Z_$]*'
key_re = re.compile(key_re_str)
path_re = re.compile('(' + key_re_str + ')?(\.' + key_re_str + ')+')
comment_re = re.compile(r'(\{!.+?!\})', flags=re.DOTALL)


def get_path_or_key(pork):
    if pork == '.':
        pk = ['path', True, []]
    elif path_re.match(pork):
        f_local = pork.startswith('.')
        if f_local:
            pork = pork[1:]
        pk = ['path', f_local, pork.split('.')]
    elif key_re.match(pork):
        pk = ['key', pork]
    else:
        raise ValueError('expected a path or key, not %r' % pork)
    return pk


def split_leading(text):
    leading_stripped = text.lstrip()
    leading_ws = text[:len(text) - len(leading_stripped)]
    return leading_ws, leading_stripped


class Token(object):
    def __init__(self, text):
        self.text = text

    def get_line_count(self):
        # returns 0 if there's only one line, because the
        # token hasn't increased the number of lines.
        count = len(self.text.splitlines()) - 1
        if self.text[-1] in ('\n', '\r'):
            count += 1
        return count

    def __repr__(self):
        cn = self.__class__.__name__
        disp = self.text
        if len(disp) > 20:
            disp = disp[:17] + '...'
        return '%s(%r)' % (cn, disp)


class CommentToken(Token):
    def to_dust_ast(self):
        return [['comment', self.text]]


class BufferToken(Token):
    def to_dust_ast(self):
        # It is hard to simulate the PEG parsing in this case,
        # especially while supporting universal newlines.
        if not self.text:
            return []
        rev = []
        remaining_lines = self.text.splitlines()
        if self.text[-1] in ('\n', '\r'):
            # kind of a bug in splitlines if you ask me.
            remaining_lines.append('')
        while remaining_lines:
            line = remaining_lines.pop()
            leading_ws, lstripped = split_leading(line)
            if remaining_lines:
                if lstripped:
                    rev.append(['buffer', lstripped])
                rev.append(['format', '\n', leading_ws])
            else:
                if line:
                    rev.append(['buffer', line])
        ret = list(reversed(rev))
        return ret


ALL_ATTRS = ('closing', 'symbol', 'refpath', 'contpath',
             'filters', 'params', 'selfclosing')


class Tag(Token):
    req_attrs = ()
    ill_attrs = ()

    def __init__(self, text, **kw):
        super(Tag, self).__init__(text)
        self._attr_dict = kw
        self.set_attrs(kw)

    @property
    def param_list(self):
        try:
            return params_to_kv(self.params)
        except AttributeError:
            return []

    @property
    def name(self):
        try:
            return self.refpath.strip().lstrip('.')
        except (AttributeError, TypeError):
            return None

    def set_attrs(self, attr_dict, raise_exc=True):
        cn = self.__class__.__name__
        all_attrs = getattr(self, 'all_attrs', ())
        if all_attrs:
            req_attrs = [a for a in ALL_ATTRS if a in all_attrs]
            ill_attrs = [a for a in ALL_ATTRS if a not in all_attrs]
        else:
            req_attrs = getattr(self, 'req_attrs', ())
            ill_attrs = getattr(self, 'ill_attrs', ())

        opt_attrs = getattr(self, 'opt_attrs', ())
        if opt_attrs:
            ill_attrs = [a for a in ill_attrs if a not in opt_attrs]
        for attr in req_attrs:
            if attr_dict.get(attr, None) is None:
                raise ValueError('%s expected %s' % (cn, attr))
        for attr in ill_attrs:
            if attr_dict.get(attr, None) is not None:
                raise ValueError('%s does not take %s' % (cn, attr))

        avail_attrs = [a for a in ALL_ATTRS if a not in ill_attrs]
        for attr in avail_attrs:
            setattr(self, attr, attr_dict.get(attr, ''))
        return True

    @classmethod
    def from_match(cls, match):
        kw = dict([(str(k), v.strip())
                   for k, v in match.groupdict().items()
                   if v is not None and v.strip()])
        obj = cls(text=match.group(0), **kw)
        obj.orig_match = match
        return obj


class BlockTag(Tag):
    all_attrs = ('contpath',)


class ReferenceTag(Tag):
    all_attrs = ('refpath',)
    opt_attrs = ('filters',)

    def to_dust_ast(self):
        pork = get_path_or_key(self.refpath)
        filters = ['filters']
        if self.filters:
            f_list = self.filters.split('|')[1:]
            for f in f_list:
                filters.append(f)
        return [['reference', pork, filters]]


class SectionTag(Tag):
    ill_attrs = ('closing')


class ClosingTag(Tag):
    all_attrs = ('closing', 'refpath')


class SpecialTag(Tag):
    all_attrs = ('symbol', 'refpath')

    def to_dust_ast(self):
        return [['special', self.refpath]]


class BlockTag(Tag):
    all_attrs = ('symbol', 'refpath')


class PartialTag(Tag):
    req_attrs = ('symbol', 'refpath', 'selfclosing')

    def __init__(self, **kw):
        super(PartialTag, self).__init__(**kw)
        self.subtokens = parse_inline(self.refpath)

    def to_dust_ast(self):
        context = ['context']
        contpath = self.contpath
        if contpath:
            context.append(get_path_or_key(contpath))
        inline_body = inline_to_dust_ast(self.subtokens)
        return [['partial',
                 inline_body,
                 context]]


def parse_inline(source):
    if not source:
        raise ParseError('empty inline token')
    if source.startswith('"') and source.endswith('"'):
        source = source[1:-1]
    if not source:
        return [BufferToken("")]
    tokens = tokenize(source, inline=True)
    return tokens


def inline_to_dust_ast(tokens):
    if tokens and all(isinstance(t, BufferToken) for t in tokens):
        body = ['literal', ''.join(t.text for t in tokens)]
    else:
        body = ['body']
        for b in tokens:
            body.extend(b.to_dust_ast())
    return body


def params_to_kv(params_str):
    ret = []
    new_k, v = None, None
    p_str = params_str.strip()
    k, _, tail = p_str.partition('=')
    while tail:
        tmp, _, tail = tail.partition('=')
        tail = tail.strip()
        if not tail:
            v = tmp
        else:
            v, new_k = tmp.split()
        ret.append((k.strip(), v.strip()))
        k = new_k
    return ret


def params_to_dust_ast(param_kv):
    ret = []
    for k, v in param_kv:
        try:
            v_body = get_path_or_key(v)
        except ValueError:
            v_body = inline_to_dust_ast(parse_inline(v))
        ret.append(['param', ['literal', k], v_body])
    return ret


def get_tag(match, inline=False):
    groups = match.groupdict()
    symbol = groups['symbol']
    closing = groups['closing']
    refpath = groups['refpath']
    if closing:
        tag_type = ClosingTag
    elif symbol is None and refpath is not None:
        tag_type = ReferenceTag
    elif symbol in '#?^<+@%':
        tag_type = SectionTag
    elif symbol == '~':
        tag_type = SpecialTag
    elif symbol == ':':
        tag_type = BlockTag
    elif symbol == '>':
        tag_type = PartialTag
    else:
        raise ParseError('invalid tag')
    if inline and tag_type not in (ReferenceTag, SpecialTag):
        raise ParseError('invalid inline tag')
    return tag_type.from_match(match)


def tokenize(source, inline=False):
    tokens = []
    com_nocom = comment_re.split(source)
    line_counts = [1]

    def _add_token(t):
        # i wish i had nonlocal so bad
        t.start_line = sum(line_counts)
        line_counts.append(t.get_line_count())
        t.end_line = sum(line_counts)
        tokens.append(t)
    for cnc in com_nocom:
        if not cnc:
            continue
        if cnc.startswith('{!') and cnc.endswith('!}'):
            _add_token(CommentToken(cnc[2:-2]))
            continue
        prev_end = 0
        start = None
        end = None
        for match in node_re.finditer(cnc):
            start, end = match.start(1), match.end(1)
            if prev_end < start:
                _add_token(BufferToken(cnc[prev_end:start]))
            prev_end = end
            try:
                _add_token(get_tag(match, inline))
            except ParseError as pe:
                pe.line_no = sum(line_counts)
                raise
        tail = cnc[prev_end:]
        if tail:
            _add_token(BufferToken(tail))
    return tokens

#########
# PARSING
#########


class Section(object):
    def __init__(self, start_tag=None, blocks=None):
        if start_tag is None:
            refpath = None
            name = '<root>'
        else:
            refpath = start_tag.refpath
            name = start_tag.name

        self.refpath = refpath
        self.name = name
        self.start_tag = start_tag
        self.blocks = blocks or []

    def add(self, obj):
        if type(obj) == Block:
            self.blocks.append(obj)
        else:
            if not self.blocks:
                self.blocks = [Block()]
            self.blocks[-1].add(obj)

    def to_dict(self):
        ret = {self.name: dict([(b.name, b.to_list()) for b in self.blocks])}
        return ret

    def to_dust_ast(self):
        symbol = self.start_tag.symbol

        pork = get_path_or_key(self.refpath)

        context = ['context']
        contpath = self.start_tag.contpath
        if contpath:
            context.append(get_path_or_key(contpath))

        params = ['params']
        param_list = self.start_tag.param_list
        if param_list:
            try:
                params.extend(params_to_dust_ast(param_list))
            except ParseError as pe:
                pe.token = self
                raise

        bodies = ['bodies']
        if self.blocks:
            for b in reversed(self.blocks):
                bodies.extend(b.to_dust_ast())

        return [[symbol,
                pork,
                context,
                params,
                bodies]]


class Block(object):
    def __init__(self, name='block'):
        if not name:
            raise ValueError('blocks need a name, not: %r' % name)
        self.name = name
        self.items = []

    def add(self, item):
        self.items.append(item)

    def to_list(self):
        ret = []
        for i in self.items:
            try:
                ret.append(i.to_dict())
            except AttributeError:
                ret.append(i)
        return ret

    def _get_dust_body(self):
        # for usage by root block in ParseTree
        ret = []
        for i in self.items:
            ret.extend(i.to_dust_ast())
        return ret

    def to_dust_ast(self):
        name = self.name
        body = ['body']
        dust_body = self._get_dust_body()
        if dust_body:
            body.extend(dust_body)
        return [['param',
                ['literal', name],
                body]]


class ParseTree(object):
    def __init__(self, root_block):
        self.root_block = root_block

    def to_dust_ast(self):
        ret = ['body']
        ret.extend(self.root_block._get_dust_body())
        return ret

    @classmethod
    def from_tokens(cls, tokens):
        root_sect = Section()
        ss = [root_sect]  # section stack
        for token in tokens:
            if type(token) == SectionTag:
                new_s = Section(token)
                ss[-1].add(new_s)
                if not token.selfclosing:
                    ss.append(new_s)
            elif type(token) == ClosingTag:
                if len(ss) <= 1:
                    msg = 'closing tag before opening tag: %r' % token
                    raise ParseError(msg, token=token)
                if token.name != ss[-1].name:
                    msg = ('improperly nested tags: %r does not close %r' %
                           (token, ss[-1].start_tag))
                    raise ParseError(msg, token=token)
                ss.pop()
            elif type(token) == BlockTag:
                if len(ss) <= 1:
                    msg = 'start block outside of a section: %r' % token
                    raise ParseError(msg, token=token)
                new_b = Block(name=token.refpath)
                ss[-1].add(new_b)
            else:
                ss[-1].add(token)
        return cls(root_sect.blocks[0])

    @classmethod
    def from_source(cls, src):
        tokens = tokenize(src)
        return cls.from_tokens(tokens)


##############
# Optimize AST
##############
DEFAULT_SPECIAL_CHARS = {'s': ' ',
                         'n': '\n',
                         'r': '\r',
                         'lb': '{',
                         'rb': '}'}

DEFAULT_OPTIMIZERS = {
    'body': 'compact_buffers',
    'special': 'convert_special',
    'format': 'nullify',
    'comment': 'nullify'}

for nsym in ('buffer', 'filters', 'key', 'path', 'literal'):
    DEFAULT_OPTIMIZERS[nsym] = 'noop'

for nsym in ('#', '?', '^', '<', '+', '@', '%', 'reference',
             'partial', 'context', 'params', 'bodies', 'param'):
    DEFAULT_OPTIMIZERS[nsym] = 'visit'

UNOPT_OPTIMIZERS = dict(DEFAULT_OPTIMIZERS)
UNOPT_OPTIMIZERS.update({'format': 'noop', 'body': 'visit'})


def escape(text, esc_func=json.dumps):
    return esc_func(text)


class Optimizer(object):
    def __init__(self, optimizers=None, special_chars=None):
        if special_chars is None:
            special_chars = DEFAULT_SPECIAL_CHARS
        self.special_chars = special_chars

        if optimizers is None:
            optimizers = DEFAULT_OPTIMIZERS
        self.optimizers = dict(optimizers)

    def optimize(self, node):
        # aka filter_node()
        nsym = node[0]
        optimizer_name = self.optimizers[nsym]
        return getattr(self, optimizer_name)(node)

    def noop(self, node):
        return node

    def nullify(self, node):
        return None

    def convert_special(self, node):
        return ['buffer', self.special_chars[node[1]]]

    def visit(self, node):
        ret = [node[0]]
        for n in node[1:]:
            filtered = self.optimize(n)
            if filtered:
                ret.append(filtered)
        return ret

    def compact_buffers(self, node):
        ret = [node[0]]
        memo = None
        for n in node[1:]:
            filtered = self.optimize(n)
            if not filtered:
                continue
            if filtered[0] == 'buffer':
                if memo is not None:
                    memo[1] += filtered[1]
                else:
                    memo = filtered
                    ret.append(filtered)
            else:
                memo = None
                ret.append(filtered)
        return ret

    def __call__(self, node):
        return self.optimize(node)


#########
# Compile
#########


ROOT_RENDER_TMPL = \
'''def render(chk, ctx):
    {body}
    return {root_func_name}(chk, ctx)
'''


def _python_compile(source, name, global_env=None):
    if global_env is None:
        global_env = {}
    else:
        global_env = dict(global_env)
    try:
        code = compile(source, '<string>', 'single')
    except:
        raise
    if PY3:
        exec(code, global_env)
    else:
        exec("exec code in global_env")
    return global_env[name]


class Compiler(object):
    """
    Note: Compiler objects aren't really meant to be reused,
    the class is just for namespacing and convenience.
    """
    sections = {'#': 'section',
                '?': 'exists',
                '^': 'notexists'}
    nodes = {'<': 'inline_partial',
             '+': 'region',
             '@': 'helper',
             '%': 'pragma'}

    def __init__(self, env=None):
        if env is None:
            env = default_env
        self.env = env

        self.bodies = {}
        self.blocks = {}
        self.block_str = ''
        self.index = 0
        self.auto = 'h'  # TODO

    def compile(self, ast, name='render'):
        python_source = self._gen_python(ast)
        return _python_compile(python_source, name)

    def _gen_python(self, ast):  # ast to init?
        lines = []
        c_node = self._node(ast)

        block_str = self._root_blocks()

        bodies = self._root_bodies()
        lines.extend(bodies.splitlines())
        if block_str:
            lines.extend(['', block_str, ''])
        body = '\n    '.join(lines)

        ret = ROOT_RENDER_TMPL.format(body=body,
                                      root_func_name=c_node)
        self.python_source = ret
        return ret

    def _root_blocks(self):
        if not self.blocks:
            self.block_str = ''
            return ''
        self.block_str = 'ctx = ctx.shift_blocks(blocks)\n    '
        pairs = ['"' + name + '": ' + fn for name, fn in self.blocks.items()]
        return 'blocks = {' + ', '.join(pairs) + '}'

    def _root_bodies(self):
        max_body = max(self.bodies.keys())
        ret = [''] * (max_body + 1)
        for i, body in self.bodies.items():
            ret[i] = ('\ndef body_%s(chk, ctx):\n    %sreturn chk%s\n'
                      % (i, self.block_str, body))
        return ''.join(ret)

    def _convert_special(self, node):
        return ['buffer', self.special_chars[node[1]]]

    def _node(self, node):
        ntype = node[0]
        if ntype in self.sections:
            stype = self.sections[ntype]
            return self._section(node, stype)
        elif ntype in self.nodes:
            ntype = self.nodes[ntype]

        cfunc = getattr(self, '_' + ntype, None)
        if not callable(cfunc):
            raise TypeError('unsupported node type: "%r"', node[0])
        return cfunc(node)

    def _body(self, node):
        index = self.index
        self.index += 1   # make into property, equal to len of bodies?
        name = 'body_%s' % index
        self.bodies[index] = self._parts(node)
        return name

    def _parts(self, body):
        parts = []
        for part in body[1:]:
            parts.append(self._node(part))
        return ''.join(parts)

    def _buffer(self, node):
        return '.write(%s)' % escape(node[1])

    def _format(self, node):
        return '.write(%s)' % escape(node[1] + node[2])

    def _reference(self, node):
        return '.reference(%s,ctx,%s)' % (self._node(node[1]),
                                          self._node(node[2]))

    def _section(self, node, cmd):
        return '.%s(%s,%s,%s,%s)' % (cmd,
                                     self._node(node[1]),
                                     self._node(node[2]),
                                     self._node(node[4]),
                                     self._node(node[3]))

    def _inline_partial(self, node):
        bodies = node[4]
        for param in bodies[1:]:
            btype = param[1][1]
            if btype == 'block':
                self.blocks[node[1][1]] = self._node(param[2])
                return ''
        return ''

    def _region(self, node):
        """aka the plus sign ('+') block"""
        tmpl = '.block(ctx.get_block(%s),%s,%s,%s)'
        return tmpl % (escape(node[1][1]),
                       self._node(node[2]),
                       self._node(node[4]),
                       self._node(node[3]))

    def _helper(self, node):
        return '.helper(%s,%s,%s,%s)' % (escape(node[1][1]),
                                         self._node(node[2]),
                                         self._node(node[4]),
                                         self._node(node[3]))

    def _pragma(self, node):
        pr_name = node[1][1]
        pragma = self.env.pragmas.get(pr_name)
        if not pragma or not callable(pragma):
            return ''  # TODO: raise?
        raw_bodies = node[4]
        bodies = {}
        for rb in raw_bodies[1:]:
            bodies[rb[1][1]] = rb[2]

        raw_params = node[3]
        params = {}
        for rp in raw_params[1:]:
            params[rp[1][1]] = rp[2][1]

        try:
            ctx = node[2][1][1]
        except (IndexError, AttributeError):
            ctx = None

        return pragma(self, ctx, bodies, params)

    def _partial(self, node):
        if node[0] == 'body':
            body_name = self._node(node[1])
            return '.partial(' + body_name + ', %s)' % self._node(node[2])
        return '.partial(%s, %s)' % (self._node(node[1]),
                                     self._node(node[2]))

    def _context(self, node):
        contpath = node[1:]
        if contpath:
            return 'ctx.rebase(%s)' % (self._node(contpath[0]))
        return 'ctx'

    def _params(self, node):
        parts = [self._node(p) for p in node[1:]]
        if parts:
            return '{' + ','.join(parts) + '}'
        return 'None'

    def _bodies(self, node):
        parts = [self._node(p) for p in node[1:]]
        return '{' + ','.join(parts) + '}'

    def _param(self, node):
        return ':'.join([self._node(node[1]), self._node(node[2])])

    def _filters(self, node):
        ret = '"%s"' % self.auto
        f_list = ['"%s"' % f for f in node[1:]]  # repr?
        if f_list:
            ret += ',[%s]' % ','.join(f_list)
        return ret

    def _key(self, node):
        return 'ctx.get(%r)' % node[1]

    def _path(self, node):
        cur = node[1]
        keys = node[2] or []
        return 'ctx.get_path(%s, %s)' % (cur, keys)

    def _literal(self, node):
        return escape(node[1])


#########
# Runtime
#########

# Escapes/filters


def escape_html(text):
    text = unicode(text)
    # TODO: dust.js doesn't use this, but maybe we should: .replace("'", '&squot;')
    return cgi.escape(text, True)


def escape_js(text):
    text = unicode(text)
    return (text
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace("'", "\\'")
            .replace('\r', '\\r')
            .replace('\u2028', '\\u2028')
            .replace('\u2029', '\\u2029')
            .replace('\n', '\\n')
            .replace('\f', '\\f')
            .replace('\t', '\\t'))


def escape_uri(text):
    return urllib.quote(text)


def escape_uri_component(text):
    return (escape_uri(text)
            .replace('/', '%2F')
            .replace('?', '%3F')
            .replace('=', '%3D')
            .replace('&', '%26'))


# Helpers

def first_helper(chunk, context, bodies, params=None):
    if context.stack.index > 0:
        return chunk
    if 'block' in bodies:
        return bodies['block'](chunk, context)
    return chunk


def last_helper(chunk, context, bodies, params=None):
    if context.stack.index < context.stack.of - 1:
        return chunk
    if 'block' in bodies:
        return bodies['block'](chunk, context)
    return chunk


def sep_helper(chunk, context, bodies, params=None):
    if context.stack.index == context.stack.of - 1:
        return chunk
    if 'block' in bodies:
        return bodies['block'](chunk, context)
    return chunk


def idx_helper(chunk, context, bodies, params=None):
    if 'block' in bodies:
        return bodies['block'](chunk, context.push(context.stack.index))
    return chunk


def idx_1_helper(chunk, context, bodies, params=None):
    if 'block' in bodies:
        return bodies['block'](chunk, context.push(context.stack.index + 1))
    return chunk


def size_helper(chunk, context, bodies, params):
    try:
        key = params['key']
        return chunk.write(str(len(key)))
    except (KeyError, TypeError):
        return chunk


def _do_compare(chunk, context, bodies, params, cmp_op):
    "utility function used by @eq, @gt, etc."
    params = params or {}
    try:
        body = bodies['block']
        key = params['key']
        value = params['value']
        typestr = params.get('type', 'string')
    except KeyError:
        return chunk
    rkey = _resolve_value(key, chunk, context)
    rvalue = _resolve_value(value, chunk, context)
    crkey, crvalue = _coerce(rkey, typestr), _coerce(rvalue, typestr)
    if isinstance(crvalue, type(crkey)) and cmp_op(crkey, crvalue):
        return chunk.render(body, context)
    elif 'else' in bodies:
        return chunk.render(bodies['else'], context)
    return chunk


def _resolve_value(item, chunk, context):
    if not callable(item):
        return item
    try:
        return chunk.tap_render(item, context)
    except:
        return None


_COERCE_MAP = {
    'number': float,
    'string': unicode,
    'boolean': bool,
}  # Not implemented: date, context


def _coerce(value, typestr):
    coerce_type = _COERCE_MAP.get(typestr.lower())
    if not coerce_type or isinstance(value, coerce_type):
        return value
    if isinstance(value, basestring):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            pass
    try:
        return coerce_type(value)
    except (TypeError, ValueError):
        return value


def _make_compare_helpers():
    from functools import partial
    from operator import eq, ne, lt, le, gt, ge
    CMP_MAP = {'eq': eq, 'ne': ne, 'gt': gt, 'lt': lt, 'gte': ge, 'lte': le}
    ret = {}
    for name, op in CMP_MAP.items():
        ret[name] = partial(_do_compare, cmp_op=op)
    return ret


DEFAULT_HELPERS = {'first': first_helper,
                   'last': last_helper,
                   'sep': sep_helper,
                   'idx': idx_helper,
                   'idx_1': idx_1_helper,
                   'size': size_helper}
DEFAULT_HELPERS.update(_make_compare_helpers())

# Actual runtime objects


class Context(object):
    def __init__(self, env, stack, global_vars=None, blocks=None):
        self.env = env
        self.stack = stack
        if global_vars is None:
            global_vars = {}
        self.globals = global_vars
        self.blocks = blocks

    @classmethod
    def wrap(cls, env, context):
        if isinstance(context, cls):
            return context
        return cls(env, Stack(context))

    def get(self, key):
        ctx = self.stack
        value = None
        while ctx:
            try:
                value = ctx.head[key]
            except (AttributeError, KeyError, TypeError):
                ctx = ctx.tail
            else:
                return value
        if value is None:
            return self.globals.get(key)
        else:
            return value

    def get_path(self, cur, down):
        ctx = self.stack
        length = len(down)  # TODO: try/except?
        if cur and not length:
            return ctx.head  # aka implicit
        try:
            ctx = ctx.head
        except AttributeError:
            return None
        for down_part in down:
            try:
                ctx = ctx[down_part]
            except (AttributeError, TypeError):
                break
            except KeyError:
                return None
        return ctx

    def push(self, head, index=None, length=None):
        return Context(self.env,
                       Stack(head, self.stack, index, length),
                       self.globals,
                       self.blocks)

    def rebase(self, head):
        return Context(self.env,
                       Stack(head),
                       self.globals,
                       self.blocks)

    def current(self):
        return self.stack.head

    def get_block(self, key):
        blocks = self.blocks
        if not blocks:
            return None
        fn = None
        for block in blocks[::-1]:
            try:
                fn = block[key]
                if fn:
                    break
            except KeyError:
                continue
        return fn

    def shift_blocks(self, local_vars):
        blocks = self.blocks
        if local_vars:
            if blocks:
                new_blocks = blocks + [local_vars]
            else:
                new_blocks = [local_vars]
            return Context(self.env, self.stack, self.globals, new_blocks)
        return self


class Stack(object):
    def __init__(self, head, tail=None, index=None, length=None):
        self.head = head
        self.tail = tail
        self.index = index or 0
        self.of = length or 1
        #self.is_object = is_scalar(head)

    def __repr__(self):
        return 'Stack(%r, %r, %r, %r)' % (self.head,
                                          self.tail,
                                          self.index,
                                          self.of)


class Stub(object):
    def __init__(self, callback):
        self.head = Chunk(self)
        self.callback = callback
        self.out = ''  # TODO: convert to list, use property and ''.join()

    def flush(self):
        chunk = self.head
        while chunk:
            if chunk.flushable:
                self.out += chunk.data
            elif chunk.error:
                self.callback(chunk.error, '')
                self.flush = lambda self: None
                return
            else:
                return
            self.head = chunk = chunk.next
        self.callback(None, self.out)


class Stream(object):
    def __init__(self):
        self.head = Chunk(self)
        self.events = {}

    def flush(self):
        chunk = self.head
        while chunk:
            if chunk.flushable:
                self.emit('data', chunk.data)
            elif chunk.error:
                self.emit('error', chunk.error)
                self.flush = lambda self: None
                return
            else:
                return
            self.head = chunk = chunk.next
        self.emit('end')

    def emit(self, etype, data=None):
        try:
            self.events[etype](data)
        except KeyError:
            pass

    def on(self, etype, callback):
        self.events[etype] = callback
        return self


def is_scalar(obj):
    return not hasattr(obj, '__iter__') or isinstance(obj, basestring)


def is_empty(obj):
    try:
        return obj is None or obj is False or len(obj) == 0
    except TypeError:
        return False


class Chunk(object):
    def __init__(self, root, next_chunk=None, taps=None):
        self.root = root
        self.next = next_chunk
        self.taps = taps
        self.data = ''
        self.flushable = False
        self.error = None

    def write(self, data):
        if self.taps:
            data = self.taps.go(data)
        self.data += data
        return self

    def end(self, data=None):
        if data:
            self.write(data)
        self.flushable = True
        self.root.flush()
        return self

    def map(self, callback):
        cursor = Chunk(self.root, self.next, self.taps)
        branch = Chunk(self.root, cursor, self.taps)
        self.next = branch
        self.flushable = True
        callback(branch)
        return cursor

    def tap(self, tap):
        if self.taps:
            self.taps = self.taps.push(tap)
        else:
            self.taps = Tap(tap)
        return self

    def untap(self):
        self.taps = self.taps.tail
        return self

    def render(self, body, context):
        return body(self, context)

    def tap_render(self, body, context):
        output = []

        def tmp_tap(data):
            if data:
                output.append(data)
            return ''
        self.tap(tmp_tap)
        self.render(body, context).untap()
        return ''.join(output)

    def reference(self, elem, context, auto, filters=None):
        if callable(elem):
            # this whole callable thing is a pretty big TODO
            elem = elem(self, context)
            if isinstance(elem, Chunk):
                return elem
        if is_empty(elem):
            return self
        else:
            filtered = context.env.apply_filters(elem, auto, filters)
            return self.write(filtered)

    def section(self, elem, context, bodies, params=None):
        if callable(elem):
            elem = elem(self, context, bodies, params)
            if isinstance(elem, Chunk):
                return elem
        body = bodies.get('block')
        else_body = bodies.get('else')
        if params:
            context = context.push(params)
        if not elem and else_body and elem is not 0:
            # breaks with dust.js; dust.js doesn't render else blocks
            # on sections referencing empty lists.
            return else_body(self, context)

        if not body or elem is None:
            return self
        if is_scalar(elem) or hasattr(elem, 'keys'):  # haaack
            if elem is True:
                return body(self, context)
            else:
                return body(self, context.push(elem))
        else:
            chunk = self
            length = len(elem)
            for i, el in enumerate(elem):
                chunk = body(chunk, context.push(el, i, length))
            return chunk

    def exists(self, elem, context, bodies, params=None):
        if not is_empty(elem):
            if bodies.get('block'):
                return bodies['block'](self, context)
        elif bodies.get('else'):
            return bodies['else'](self, context)
        return self

    def notexists(self, elem, context, bodies, params=None):
        if is_empty(elem):
            if bodies.get('block'):
                return bodies['block'](self, context)
        elif bodies.get('else'):
            return bodies['else'](self, context)
        return self

    def block(self, elem, context, bodies, params=None):
        body = bodies.get('block')
        if elem:
            body = elem
        if body:
            body(self, context)
        return self

    def partial(self, elem, context, bodies=None):
        if callable(elem):
            cback = lambda name, chk: context.env.load_chunk(name, chk, context).end()
            return self.capture(elem, context, cback)
        return context.env.load_chunk(elem, self, context)

    def helper(self, name, context, bodies, params=None):
        return context.env.helpers[name](self, context, bodies, params)

    def capture(self, body, context, callback):
        def map_func(chunk):
            def stub_cb(err, out):
                if err:
                    chunk.set_error(err)
                else:
                    callback(out, chunk)
            stub = Stub(stub_cb)
            body(stub.head, context).end()
        return self.map(map_func)

    def set_error(self, error):
        self.error = error
        self.root.flush()
        return self


class Tap(object):
    def __init__(self, head=None, tail=None):
        self.head = head
        self.tail = tail

    def push(self, tap):
        return Tap(tap, self)

    def go(self, value):
        tap = self
        while tap:
            value = tap.head(value)  # TODO: type errors?
            tap = tap.tail
        return value


DEFAULT_FILTERS = {
    'h': escape_html,
    'j': escape_js,
    'u': escape_uri,
    'uc': escape_uri_component}


#########
# Pragmas
#########


def esc_pragma(compiler, context, bodies, params):
    old_auto = compiler.auto
    if not context:
        context = 'h'
    if context == 's':
        compiler.auto = ''
    else:
        compiler.auto = context
    out = compiler._parts(bodies['block'])
    compiler.auto = old_auto
    return out


DEFAULT_PRAGMAS = {
    'esc': esc_pragma
}


###########
# Interface
###########


class Template(object):
    def __init__(self,
                 name,
                 source,
                 source_file=None,
                 optimize=True,
                 keep_source=True,
                 env=None,
                 lazy=False):
        self.name = name
        self.source = source
        self.source_file = source_file
        self.last_mtime = None
        if source_file:
            self.last_mtime = os.path.getmtime(source_file)
        self.optimized = optimize
        if env is None:
            env = default_env
        self.env = env

        if lazy:  # lazy is really only for testing
            self.render_func = None
            return
        self.render_func = self._get_render_func(optimize)
        if not keep_source:
            self.source = None

    def render(self, model, env=None):
        env = env or self.env
        rendered = []

        def tmp_cb(err, result):
            # TODO: get rid of
            if err:
                print('Error on template %r: %r' % (self.name, err))
                raise RenderException(err)
            else:
                rendered.append(result)
                return result

        chunk = Stub(tmp_cb).head
        self.render_chunk(chunk, Context.wrap(env, model)).end()
        return rendered[0]

    def render_chunk(self, chunk, context):
        if not self.render_func:
            # to support laziness for testing
            self.render_func = self._get_render_func()
        return self.render_func(chunk, context)

    def _get_tokens(self):
        if not self.source:
            return None
        return tokenize(self.source)

    def _get_ast(self, optimize=False, raw=False):
        if not self.source:
            return None
        try:
            dast = ParseTree.from_source(self.source).to_dust_ast()
        except ParseError as pe:
            pe.source_file = self.source_file
            raise
        if raw:
            return dast
        return self.env.filter_ast(dast, optimize)

    def _get_render_func(self, optimize=True, ret_str=False):
        # switching over to optimize=True by default because it
        # makes the output easier to read and more like dust's docs
        ast = self._get_ast(optimize)
        if not ast:
            return None
        compiler = Compiler(self.env)
        func = compiler.compile(ast)
        if ret_str:
            # for testing/dev purposes
            return Compiler(self.env)._gen_python(ast)
        return func


class AshesException(Exception):
    pass


class TemplateNotFound(AshesException):
    pass


class RenderException(AshesException):
    pass


class ParseError(AshesException):
    token = None
    source_file = None

    def __init__(self, message, line_no=None, token=None):
        self.message = message
        self.token = token
        self._line_no = line_no

        super(ParseError, self).__init__(self.__str__())

    @property
    def line_no(self):
        if self._line_no:
            return self._line_no
        if getattr(self.token, 'start_line', None) is not None:
            return self.token.start_line
        return None

    @line_no.setter
    def set_line_no(self, val):
        self._line_no = val

    def __str__(self):
        msg = self.message
        infos = []
        if self.source_file:
            infos.append('in %s' % self.source_file)
        if self.line_no is not None:
            infos.append('line %s' % self.line_no)
        if infos:
            msg += ' (%s)' % ' - '.join(infos)
        return msg


class BaseAshesEnv(object):
    def __init__(self,
                 loaders=None,
                 helpers=None,
                 filters=None,
                 special_chars=None,
                 optimizers=None,
                 pragmas=None,
                 auto_reload=True):
        self.templates = {}
        self.loaders = list(loaders or [])
        self.filters = dict(DEFAULT_FILTERS)
        if filters:
            self.filters.update(filters)
        self.helpers = dict(DEFAULT_HELPERS)
        if helpers:
            self.helpers.update(helpers)
        self.special_chars = dict(DEFAULT_SPECIAL_CHARS)
        if special_chars:
            self.special_chars.update(special_chars)
        self.optimizers = dict(DEFAULT_OPTIMIZERS)
        if optimizers:
            self.optimizers.update(optimizers)
        self.pragmas = dict(DEFAULT_PRAGMAS)
        if pragmas:
            self.pragmas.update(pragmas)
        self.auto_reload = auto_reload

    def render(self, name, model):
        tmpl = self.load(name)
        return tmpl.render(model, self)

    def load(self, name):
        try:
            template = self.templates[name]
        except KeyError:
            template = self._load_template(name)
            self.register(template)
        if self.auto_reload:
            if not getattr(template, 'source_file', None):
                return template
            mtime = os.path.getmtime(template.source_file)
            if mtime > template.last_mtime:
                template = self._load_template(name)
                self.register(template)
        return self.templates[name]

    def _load_template(self, name):
        for loader in self.loaders:
            try:
                source = loader.load(name, env=self)
            except TemplateNotFound:
                continue
            else:
                return source
        raise TemplateNotFound(name)

    def load_all(self, do_register=True, **kw):
        all_tmpls = []
        for loader in reversed(self.loaders):
            # reversed so the first loader to have a template
            # will take precendence on registration
            if callable(getattr(loader, 'load_all', None)):
                tmpls = loader.load_all(self, **kw)
                all_tmpls.extend(tmpls)
                if do_register:
                    for t in tmpls:
                        self.register(t)
        return all_tmpls

    def register(self, template, name=None):
        if name is None:
            name = template.name
        self.templates[name] = template
        return

    def register_source(self, name, source, **kw):
        kw['env'] = self
        tmpl = Template(name, source, **kw)
        self.register(tmpl)
        return tmpl

    def filter_ast(self, ast, optimize=True):
        if optimize:
            optimizers = self.optimizers
        else:
            optimizers = UNOPT_OPTIMIZERS
        optimizer = Optimizer(optimizers, self.special_chars)
        return optimizer.optimize(ast)

    def apply_filters(self, string, auto, filters):
        filters = filters or []
        if auto and 's' not in filters and auto not in filters:
            filters = filters + [auto]
        for f in filters:
            filt_fn = self.filters.get(f)
            if filt_fn:
                string = filt_fn(string)
        return string

    def load_chunk(self, name, chunk, context):
        try:
            tmpl = self.load(name)
        except TemplateNotFound as tnf:
            return chunk.set_error(tnf)
        return tmpl.render_chunk(chunk, context)


class AshesEnv(BaseAshesEnv):
    """
    A slightly more accessible Ashes environment, with more
    user-friendly options exposed.
    """
    def __init__(self, paths=None, keep_whitespace=False, *a, **kw):
        self.paths = list(paths or [])
        self.keep_whitespace = keep_whitespace
        exts = list(kw.pop('exts', DEFAULT_EXTENSIONS))

        super(AshesEnv, self).__init__(*a, **kw)

        for path in self.paths:
            tpl = TemplatePathLoader(path, exts)
            self.loaders.append(tpl)

    def filter_ast(self, ast, optimize=None):
        optimize = not self.keep_whitespace  # preferences override
        return super(AshesEnv, self).filter_ast(ast, optimize)

    def load_all(self):
        ret = []
        for loader in self.loaders:
            ret.extend(loader.load_all(self))
        return ret


DEFAULT_EXTENSIONS = ('.dust', '.html', '.xml')


def walk_ext_matches(path, exts=None):
    if exts is None:
        exts = DEFAULT_EXTENSIONS
    exts = list(['.' + e.lstrip('.') for e in exts])
    matches = []
    for root, _, filenames in os.walk(path):
        for fn in filenames:
            for ext in exts:
                if fn.endswith(ext):
                    matches.append(os.path.join(root, fn))
    return matches


class TemplatePathLoader(object):
    def __init__(self, root_path, exts=None, encoding='utf-8'):
        self.root_path = os.path.normpath(root_path)
        self.encoding = encoding
        self.exts = exts or list(DEFAULT_EXTENSIONS)

    def load(self, path, env=None):
        env = env or default_env
        norm_path = os.path.normpath(path)
        if path.startswith('../'):
            raise ValueError('no traversal above loader root path: %r' % path)
        if not path.startswith(self.root_path):
            norm_path = os.path.join(self.root_path, norm_path)
        abs_path = os.path.abspath(norm_path)
        if os.path.isfile(abs_path):
            with codecs.open(abs_path, 'r', self.encoding) as f:
                source = f.read()
        else:
            raise TemplateNotFound(path)
        template = Template(path, source, abs_path, env=env)
        return template

    def load_all(self, env, exts=None, **kw):
        ret = []
        exts = exts or self.exts
        tmpl_paths = walk_ext_matches(self.root_path, exts)
        for tmpl_path in tmpl_paths:
            ret.append(self.load(tmpl_path, env))
        return ret


class FlatteningPathLoader(TemplatePathLoader):
    """
    I've seen this mode of using dust templates in a couple places,
    but really it's lazy and too ambiguous. It increases the chances
    of silent conflicts and makes it hard to tell which templates refer
    to which just by looking at the template code.
    """
    def __init__(self, *a, **kw):
        self.keep_ext = kw.pop('keep_ext', True)
        super(FlatteningPathLoader, self).__init__(*a, **kw)

    def load(self, *a, **kw):
        tmpl = super(FlatteningPathLoader, self).load(*a, **kw)
        name = os.path.basename(tmpl.name)
        if not self.keep_ext:
            name, ext = os.path.splitext(name)
        tmpl.name = name
        return tmpl

try:
    import bottle
except ImportError:
    pass
else:
    class AshesBottleTemplate(bottle.BaseTemplate):
        extensions = list(bottle.BaseTemplate.extensions)
        extensions.extend(['ash', 'ashes', 'dust'])

        def prepare(self, **options):
            if not self.source:
                self.source = self._load_source(self.name)
                if self.source is None:
                    raise TemplateNotFound(self.name)

            options['name'] = self.name
            options['source'] = self.source
            options['source_file'] = self.filename
            for key in ('optimize', 'keep_source', 'env'):
                if key in self.settings:
                    options.setdefault(key, self.settings[key])
            env = self.settings.get('env', default_env)
            # I truly despise 2.6.4's unicode kwarg bug
            options = dict([(str(k), v) for k, v in options.iteritems()])
            self.tpl = env.register_source(**options)

        def _load_source(self, name):
            fname = self.search(name, self.lookup)
            if not fname:
                return
            with codecs.open(fname, "rb", self.encoding) as f:
                return f.read()

        def render(self, *a, **kw):
            for dictarg in a:
                kw.update(dictarg)
            context = self.defaults.copy()
            context.update(kw)
            return self.tpl.render(context)

    from functools import partial as _fp
    ashes_bottle_template = _fp(bottle.template,
                                template_adapter=AshesBottleTemplate)
    ashes_bottle_view = _fp(bottle.view,
                            template_adapter=AshesBottleTemplate)
    del bottle
    del _fp


ashes = default_env = AshesEnv()


def _main():
    # TODO: accidentally unclosed tags may consume
    # trailing buffers without warning
    try:
        tmpl = ('{@eq key=hello value="True" type="boolean"}'
                '{hello}, world'
                '{:else}'
                'oh well, world'
                '{/eq}'
                ', {@size key=hello/} characters')
        ashes.register_source('hi', tmpl)
        print(ashes.render('hi', {'hello': 'greetings'}))
    except Exception as e:
        import pdb;pdb.post_mortem()
        raise

if __name__ == '__main__':
    _main()
