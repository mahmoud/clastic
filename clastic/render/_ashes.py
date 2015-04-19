# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import cgi
import sys
import json
import codecs
import pprint
import string
import fnmatch


PY3 = (sys.version_info[0] == 3)
if PY3:
    unicode, string_types = str, (str, bytes)
else:
    string_types = (str, unicode)

__version__ = '0.7.4'
__author__ = 'Mahmoud Hashemi'
__contact__ = 'mahmoudrhashemi@gmail.com'
__url__ = 'https://github.com/mahmoud/ashes'
__license__ = 'BSD'


DEFAULT_EXTENSIONS = ('.dust', '.html', '.xml')
DEFAULT_IGNORED_PATTERNS = ('.#*',)


# need to add group for literals
# switch to using word boundary for params section
node_re = re.compile(r'({'
                     r'(?P<closing>\/)?'
                     r'(?:(?P<symbol>[\~\#\?\@\:\<\>\+\^\%])\s*)?'
                     r'(?P<refpath>[a-zA-Z0-9_\$\.]+|"[^"]+")'
                     r'(?:\:(?P<contpath>[a-zA-Z0-9\$\.]+))?'
                     r'(?P<filters>[\|a-z]+)*?'
                     r'(?P<params>(?:\s+\w+\=(("[^"]*?")|([\w\.]+)))*)?'
                     r'\s*'
                     r'(?P<selfclosing>\/)?'
                     r'\})',
                     flags=re.MULTILINE)

key_re_str = '[a-zA-Z_$][0-9a-zA-Z_$]*'
key_re = re.compile(key_re_str)
path_re = re.compile('(' + key_re_str + ')?(\.' + key_re_str + ')+')
comment_re = re.compile(r'(\{!.+?!\})|(\{`.+?`\})', flags=re.DOTALL)


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


class RawToken(Token):
    def to_dust_ast(self):
        return [['raw', self.text]]


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
        """
            2014.05.09
                This brings compatibility to the more popular fork of Dust.js
                from LinkedIn (v1.0)

                Adding in `params` so `partials` function like sections.
        """
        context = ['context']
        contpath = self.contpath
        if contpath:
            context.append(get_path_or_key(contpath))

        params = ['params']
        param_list = self.param_list
        if param_list:
            try:
                params.extend(params_to_dust_ast(param_list))
            except ParseError as pe:
                pe.token = self
                raise

        ## tying to make this more standardized
        inline_body = inline_to_dust_ast(self.subtokens)
        return [['partial',
                 inline_body,
                 context,
                 params,
                 ]]


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
        raise ParseError('invalid tag symbol: %r' % symbol)
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
        elif cnc.startswith('{!') and cnc.endswith('!}'):
            _add_token(CommentToken(cnc[2:-2]))
            continue
        elif cnc.startswith('{`') and cnc.endswith('`}'):
            _add_token(RawToken(cnc[2:-2]))
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
                    msg = 'closing tag before opening tag: %r' % token.text
                    raise ParseError(msg, token=token)
                if token.name != ss[-1].name:
                    msg = ('improperly nested tags: %r does not close %r' %
                           (token.text, ss[-1].start_tag.text))
                    raise ParseError(msg, token=token)
                ss.pop()
            elif type(token) == BlockTag:
                if len(ss) <= 1:
                    msg = 'start block outside of a section: %r' % token.text
                    raise ParseError(msg, token=token)
                new_b = Block(name=token.refpath)
                ss[-1].add(new_b)
            else:
                ss[-1].add(token)
        if len(ss) > 1:
            raise ParseError('unclosed tag: %r' % ss[-1].start_tag.text,
                             token=ss[-1].start_tag)
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

for nsym in ('buffer', 'filters', 'key', 'path', 'literal', 'raw'):
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

    def _raw(self, node):
        return '.write(%r)' % node[1]

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
        """
        2014.05.09
          This brings compatibility to the more popular fork of Dust.js
          from LinkedIn (v1.0)

          Adding in `params` so `partials` function like sections.
          updating call to .partial() to include the kwargs

          dust.js reference :
                compile.nodes = {
                    partial: function(context, node) {
                      return '.partial(' +
                          compiler.compileNode(context, node[1]) +
                          ',' + compiler.compileNode(context, node[2]) +
                          ',' + compiler.compileNode(context, node[3]) + ')';
                    },
        """
        if node[0] == 'body':
            body_name = self._node(node[1])
            return '.partial(' + body_name + ', %s)' % self._node(node[2])
        return '.partial(%s, %s, %s)' % (self._node(node[1]),
                                         self._node(node[2]),
                                         self._node(node[3]))

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


class UndefinedValueType(object):
    def __repr__(self):
        return self.__class__.__name__ + '()'

    def __str__(self):
        return ''


UndefinedValue = UndefinedValueType()

# Prerequisites for escape_url_path


def _make_quote_map(allowed_chars):
    ret = {}
    for i, c in zip(range(256), str(bytearray(range(256)))):
        ret[c] = c if c in allowed_chars else '%{0:02X}'.format(i)
    return ret

# The unreserved URI characters (per RFC 3986)
_UNRESERVED_CHARS = (frozenset(string.ascii_letters)
                     | frozenset(string.digits)
                     | frozenset('-._~'))
_RESERVED_CHARS = frozenset(":/?#[]@!$&'()*+,;=")
_PCT_ENCODING = (frozenset('%')
                 | frozenset(string.hexdigits))
_ALLOWED_CHARS = _UNRESERVED_CHARS | _RESERVED_CHARS | _PCT_ENCODING

_PATH_QUOTE_MAP = _make_quote_map(_ALLOWED_CHARS - set('?#'))


def escape_uri_path(text, to_bytes=True):
    if not to_bytes:
        return unicode().join([_PATH_QUOTE_MAP.get(c, c) for c in text])
    try:
        bytestr = text.encode('utf-8')
    except UnicodeDecodeError:
        bytestr = text
    except:
        raise ValueError('expected text or UTF-8 encoded bytes, not %r' % text)
    return ''.join([_PATH_QUOTE_MAP[b] for b in bytestr])


# Escapes/filters


def escape_html(text):
    text = unicode(text)
    # TODO: dust.js doesn't use this, but maybe we should:
    # .replace("'", '&squot;')
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


def escape_uri_component(text):
    return (escape_uri_path(text)
            .replace('/', '%2F')
            .replace('?', '%3F')
            .replace('=', '%3D')
            .replace('&', '%26'))


def comma_num(val):
    try:
        return '{0:,}'.format(val)
    except ValueError:
        return str(val)


def pp_filter(val):
    try:
        return pprint.pformat(val)
    except:
        try:
            return repr(val)
        except:
            return 'unreprable object %s' % object.__repr__(val)


JSON_PP_INDENT = 2


def ppjson_filter(val):
    "A best-effort pretty-printing filter, based on the JSON module"
    try:
        return json.dumps(val, indent=JSON_PP_INDENT, sort_keys=True)
    except TypeError:
        return unicode(val)


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


def _sort_iterate_items(items, sort_key, direction):
    if not items:
        return items
    reverse = False
    if direction == 'desc':
        reverse = True
    if not sort_key:
        sort_key = 0
    elif sort_key[0] == '$':
        sort_key = sort_key[1:]
    if sort_key == 'key':
        sort_key = 0
    elif sort_key == 'value':
        sort_key = 1
    else:
        try:
            sort_key = int(sort_key)
        except:
            sort_key = 0
    return sorted(items, key=lambda x: x[sort_key], reverse=reverse)


def iterate_helper(chunk, context, bodies, params):
    params = params or {}
    body = bodies.get('block')
    sort = params.get('sort')
    sort_key = params.get('sort_key')
    target = params.get('key')
    if not body or not target:
        return chunk  # log error
    try:
        iter(target)
    except:
        return chunk  # log error
    try:
        items = target.items()
        is_dict = True
    except:
        items = target
        is_dict = False
    if sort:
        try:
            items = _sort_iterate_items(items, sort_key, direction=sort)
        except:
            return chunk  # log error
    if is_dict:
        for key, value in items:
            body(chunk, context.push({'$key': key,
                                      '$value': value,
                                      '$type': type(value).__name__,
                                      '$0': key,
                                      '$1': value}))
    else:
        # all this is for iterating over tuples and the like
        for values in items:
            try:
                key = values[0]
            except:
                key, value = None, None
            else:
                try:
                    value = values[1]
                except:
                    value = None
            new_scope = {'$key': key,
                         '$value': value,
                         '$type': type(value).__name__}
            try:
                for i, value in enumerate(values):
                    new_scope['$%s' % i] = value
            except TypeError:
                return chunk
            else:
                body(chunk, context.push(new_scope))
    return chunk


def _do_compare(chunk, context, bodies, params, cmp_op):
    "utility function used by @eq, @gt, etc."
    params = params or {}
    try:
        body = bodies['block']
        key = params['key']
        value = params['value']
        typestr = params.get('type')
    except KeyError:
        return chunk
    rkey = _resolve_value(key, chunk, context)
    if not typestr:
        typestr = _COERCE_REV_MAP.get(type(rkey), 'string')
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
    except TypeError:
        if getattr(context, 'is_strict', None):
            raise
        return item


_COERCE_MAP = {
    'number': float,
    'string': unicode,
    'boolean': bool,
}  # Not implemented: date, context
_COERCE_REV_MAP = dict([(v, k) for k, v in _COERCE_MAP.items()])
_COERCE_REV_MAP[int] = 'number'
try:
    _COERCE_REV_MAP[long] = 'number'
except NameError:
    pass


def _coerce(value, typestr):
    coerce_type = _COERCE_MAP.get(typestr.lower())
    if not coerce_type or isinstance(value, coerce_type):
        return value
    if isinstance(value, string_types):
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
                   'size': size_helper,
                   'iterate': iterate_helper}
DEFAULT_HELPERS.update(_make_compare_helpers())


def make_base(env, stack, global_vars=None):
    """`make_base( env, stack, global_vars=None )`
        `env` and `stack` are required by the Python implementation.
        `global_vars` is optional. set to global_vars.

    2014.05.09
        This brings compatibility to the more popular fork of Dust.js
        from LinkedIn (v1.0)

        adding this to try and create compatibility with Dust

        this is used for the non-activated alternative approach of rendering a
        partial with a custom context object

          dust.makeBase = function(global) {
            return new Context(new Stack(), global);
          };
    """
    return Context(env, stack, global_vars)


# Actual runtime objects

class Context(object):
    """\
    The context is a special object that handles variable lookups and
    controls template behavior. It is the interface between your
    application logic and your templates. The context can be
    visualized as a stack of objects that grows as we descend into
    nested sections.

    When looking up a key, Dust searches the context stack from the
    bottom up. There is no need to merge helper functions into the
    template data; instead, create a base context onto which you can
    push your local template data.
    """
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

    def get(self, path, cur=False):
        "Retrieves the value `path` as a key from the context stack."
        if isinstance(path, (str, unicode)):
            if path[0] == '.':
                cur = True
                path = path[1:]
            path = path.split('.')
        return self._get(cur, path)

    def get_path(self, cur, down):
        return self._get(cur, down)

    def _get(self, cur, down):
        # many thanks to jvanasco for his contribution -mh 2014
        """
           * Get a value from the context
           * @method `_get`
           * @param {boolean} `cur` Get only from the current context
           * @param {array} `down` An array of each step in the path
           * @private
           * @return {string | object}
        """
        ctx = self.stack
        length = 0 if not down else len(down)  # TODO: try/except?

        if not length:
            # wants nothing?  ok, send back the entire payload
            return ctx.head

        first_path_element = down[0]

        value = UndefinedValue

        if cur and not length:
            ctx = ctx.head
        else:
            if not cur:
                # Search up the stack for the first_path_element value
                while ctx:
                    if isinstance(ctx.head, dict):
                        if first_path_element in ctx.head:
                            value = ctx.head[first_path_element]
                            break
                    ctx = ctx.tail
                if value is UndefinedValue:
                    if first_path_element in self.globals:
                        ctx = self.globals[first_path_element]
                    else:
                        ctx = UndefinedValue
                else:
                    ctx = value
            else:
                #if scope is limited by a leading dot, don't search up the tree
                if first_path_element in ctx.head:
                    ctx = ctx.head[first_path_element]
                else:
                    ctx = UndefinedValue

            i = 1
            while ctx and ctx is not UndefinedValue and i < length:
                if down[i] in ctx:
                    ctx = ctx[down[i]]
                else:
                    ctx = UndefinedValue
                i += 1

            if ctx is UndefinedValue:
                return None
            else:
                return ctx

    def push(self, head, index=None, length=None):
        """\
        Pushes an arbitrary value `head` onto the context stack and returns
        a new `Context` instance. Specify `index` and/or `length` to enable
        enumeration helpers."""
        return Context(self.env,
                       Stack(head, self.stack, index, length),
                       self.globals,
                       self.blocks)

    def rebase(self, head):
        """\
        Returns a new context instance consisting only of the value at
        `head`, plus any previously defined global object."""
        return Context(self.env,
                       Stack(head),
                       self.globals,
                       self.blocks)

    def current(self):
        """Returns the head of the context stack."""
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
        self._out = []

    @property
    def out(self):
        return ''.join(self._out)

    def flush(self):
        chunk = self.head
        while chunk:
            if chunk.flushable:
                self._out.append(chunk.data)
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
    return not hasattr(obj, '__iter__') or isinstance(obj, string_types)


def is_empty(obj):
    try:
        return obj is None or obj is False or len(obj) == 0
    except TypeError:
        return False


class Chunk(object):
    """\
    A Chunk is a Dust primitive for controlling the flow of the
    template. Depending upon the behaviors defined in the context,
    templates may output one or more chunks during rendering. A
    handler that writes to a chunk directly must return the modified
    chunk.
    """
    def __init__(self, root, next_chunk=None, taps=None):
        self.root = root
        self.next = next_chunk
        self.taps = taps
        self._data, self.data = [], ''
        self.flushable = False
        self.error = None

    def write(self, data):
        "Writes data to this chunk's buffer"
        if self.taps:
            data = self.taps.go(data)
        self._data.append(data)
        return self

    def end(self, data=None):
        """\
        Writes data to this chunk's buffer and marks it as flushable. This
        method must be called on any chunks created via chunk.map. Do
        not call this method on a handler's main chunk -- dust.render
        and dust.stream take care of this for you.
        """
        if data:
            self.write(data)
        self.data = ''.join(self._data)
        self.flushable = True
        self.root.flush()
        return self

    def map(self, callback):
        """\
        Creates a new chunk and passes it to `callback`. Use map to wrap
        asynchronous functions and to partition the template for
        streaming.  chunk.map tells Dust to manufacture a new chunk,
        reserving a slot in the output stream before continuing on to
        render the rest of the template. You must (eventually) call
        chunk.end() on a mapped chunk to weave its content back into
        the stream.
        """
        cursor = Chunk(self.root, self.next, self.taps)
        branch = Chunk(self.root, cursor, self.taps)
        self.next = branch
        self.data = ''.join(self._data)
        self.flushable = True
        callback(branch)
        return cursor

    def tap(self, tap):
        "Convenience methods for applying filters to a stream."
        if self.taps:
            self.taps = self.taps.push(tap)
        else:
            self.taps = Tap(tap)
        return self

    def untap(self):
        "Convenience methods for applying filters to a stream."
        self.taps = self.taps.tail
        return self

    def render(self, body, context):
        """\
        Renders a template block, such as a default block or an else
        block. Basically equivalent to body(chunk, context).
        """
        return body(self, context)

    def tap_render(self, body, context):
        output = []

        def tmp_tap(data):
            if data:
                output.append(data)
            return ''
        self.tap(tmp_tap)
        try:
            self.render(body, context)
        finally:
            self.untap()
        return ''.join(output)

    def reference(self, elem, context, auto, filters=None):
        """\
        These methods implement Dust's default behavior for keys,
        sections, blocks, partials and context helpers. While it is
        unlikely you'll need to modify these methods or invoke them
        from within handlers, the source code may be a useful point of
        reference for developers.
        """
        if callable(elem):
            # this whole callable thing is a quirky thing about dust
            try:
                elem = elem(self, context)
            except TypeError:
                if getattr(context, 'is_strict', None):
                    raise
                elem = repr(elem)
            else:
                if isinstance(elem, Chunk):
                    return elem
        if is_empty(elem):
            return self
        else:
            filtered = context.env.apply_filters(elem, auto, filters)
            return self.write(filtered)

    def section(self, elem, context, bodies, params=None):
        """\
        These methods implement Dust's default behavior for keys, sections,
        blocks, partials and context helpers. While it is unlikely you'll need
        to modify these methods or invoke them from within handlers, the
        source code may be a useful point of reference for developers."""
        if callable(elem):
            try:
                elem = elem(self, context, bodies, params)
            except TypeError:
                if getattr(context, 'is_strict', None):
                    raise
                elem = repr(elem)
            else:
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
        """\
        These methods implement Dust's default behavior for keys, sections,
        blocks, partials and context helpers. While it is unlikely you'll need
        to modify these methods or invoke them from within handlers, the
        source code may be a useful point of reference for developers."""
        if not is_empty(elem):
            if bodies.get('block'):
                return bodies['block'](self, context)
        elif bodies.get('else'):
            return bodies['else'](self, context)
        return self

    def notexists(self, elem, context, bodies, params=None):
        """\
        These methods implement Dust's default behavior for keys,
        sections, blocks, partials and context helpers. While it is
        unlikely you'll need to modify these methods or invoke them
        from within handlers, the source code may be a useful point of
        reference for developers.
        """
        if is_empty(elem):
            if bodies.get('block'):
                return bodies['block'](self, context)
        elif bodies.get('else'):
            return bodies['else'](self, context)
        return self

    def block(self, elem, context, bodies, params=None):
        """\
        These methods implement Dust's default behavior for keys,
        sections, blocks, partials and context helpers. While it is
        unlikely you'll need to modify these methods or invoke them
        from within handlers, the source code may be a useful point of
        reference for developers.
        """
        body = bodies.get('block')
        if elem:
            body = elem
        if body:
            body(self, context)
        return self

    def partial(self, elem, context, params=None):
        """These methods implement Dust's default behavior for keys, sections,
        blocks, partials and context helpers. While it is unlikely you'll need
        to modify these methods or invoke them from within handlers, the
        source code may be a useful point of reference for developers.
        """
        if params:
            context = context.push(params)
        if callable(elem):
            _env = context.env
            cback = lambda name, chk: _env.load_chunk(name, chk, context).end()
            return self.capture(elem, context, cback)
        return context.env.load_chunk(elem, self, context)

    def helper(self, name, context, bodies, params=None):
        """\
        These methods implement Dust's default behavior for keys,
        sections, blocks, partials and context helpers. While it is
        unlikely you'll need to modify these methods or invoke them
        from within handlers, the source code may be a useful point of
        reference for developers.
        """
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
        "Sets an error on this chunk and immediately flushes the output."
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

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r, %r)' % (cn, self.head, self.tail)


def to_unicode(obj):
    try:
        return unicode(obj)
    except UnicodeDecodeError:
        return unicode(obj, encoding='utf8')


DEFAULT_FILTERS = {
    'h': escape_html,
    's': to_unicode,
    'j': escape_js,
    'u': escape_uri_path,
    'uc': escape_uri_component,
    'cn': comma_num,
    'pp': pp_filter,
    'ppjson': ppjson_filter}


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

    @classmethod
    def from_path(cls, path, name=None, encoding='utf-8', **kw):
        abs_path = os.path.abspath(path)
        if not os.path.isfile(abs_path):
            raise TemplateNotFound(abs_path)
        with codecs.open(abs_path, 'r', encoding) as f:
            source = f.read()
        if not name:
            name = path
        return cls(name=name, source=source, source_file=abs_path, **kw)

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

    def __repr__(self):
        cn = self.__class__.__name__
        name, source_file = self.name, self.source_file
        if not source_file:
            return '<%s name=%r>' % (cn, name)
        return '<%s name=%r source_file=%r>' % (cn, name, source_file)


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
    template_type = Template

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

    def register_path(self, path, name=None, **kw):
        """\
        Reads in, compiles, and registers a single template from a specific
        path to a file containing the dust source code.
        """
        kw['env'] = self
        ret = self.template_type.from_path(path=path, name=name, **kw)
        self.register(ret)
        return ret

    def register_source(self, name, source, **kw):
        """\
        Compiles and registers a single template from source code
        string. Assumes caller already decoded the source string.
        """
        kw['env'] = self
        ret = self.template_type(name=name, source=source, **kw)
        self.register(ret)
        return ret

    def filter_ast(self, ast, optimize=True):
        if optimize:
            optimizers = self.optimizers
        else:
            optimizers = UNOPT_OPTIMIZERS
        optimizer = Optimizer(optimizers, self.special_chars)
        return optimizer.optimize(ast)

    def apply_filters(self, string, auto, filters):
        filters = filters or []
        if not filters:
            if auto:
                filters = ['s', auto]
            else:
                filters = ['s']
        elif filters[-1] != 's':
            if auto and auto not in filters:
                filters += ['s', auto]
            else:
                filters += ['s']
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

    def __iter__(self):
        return self.templates.itervalues()


class AshesEnv(BaseAshesEnv):
    """
    A slightly more accessible Ashes environment, with more
    user-friendly options exposed.
    """
    def __init__(self, paths=None, keep_whitespace=True, *a, **kw):
        if isinstance(paths, string_types):
            paths = [paths]
        self.paths = list(paths or [])
        self.keep_whitespace = keep_whitespace
        self.is_strict = kw.pop('is_strict', False)
        exts = list(kw.pop('exts', DEFAULT_EXTENSIONS))

        super(AshesEnv, self).__init__(*a, **kw)

        for path in self.paths:
            tpl = TemplatePathLoader(path, exts)
            self.loaders.append(tpl)

    def filter_ast(self, ast, optimize=None):
        optimize = not self.keep_whitespace  # preferences override
        return super(AshesEnv, self).filter_ast(ast, optimize)


def iter_find_files(directory, patterns, ignored=None):
    """\
    Finds files under a `directory`, matching `patterns` using "glob"
    syntax (e.g., "*.txt"). It's also possible to ignore patterns with
    the `ignored` argument, which uses the same format as `patterns.

    (from osutils.py in the boltons package)
    """
    if isinstance(patterns, string_types):
        patterns = [patterns]
    pats_re = re.compile('|'.join([fnmatch.translate(p) for p in patterns]))

    if not ignored:
        ignored = []
    elif isinstance(ignored, string_types):
        ignored = [ignored]
    ign_re = re.compile('|'.join([fnmatch.translate(p) for p in ignored]))
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if pats_re.match(basename):
                if ignored and ign_re.match(basename):
                    continue
                filename = os.path.join(root, basename)
                yield filename
    return


def walk_ext_matches(path, exts=None, ignored=None):
    if exts is None:
        exts = DEFAULT_EXTENSIONS
    if ignored is None:
        ignored = DEFAULT_IGNORED_PATTERNS
    patterns = list(['*.' + e.lstrip('*.') for e in exts])

    return sorted(iter_find_files(directory=path,
                                  patterns=patterns,
                                  ignored=ignored))


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
        template_name = os.path.relpath(abs_path, self.root_path)
        template_type = env.template_type
        return template_type.from_path(name=template_name,
                                       path=abs_path,
                                       encoding=self.encoding,
                                       env=env)

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
        #print(ashes.render('hi', {'hello': lambda x: None}))
    except Exception as e:
        import pdb;pdb.post_mortem()
        raise

    ae = AshesEnv(filters={'cn': comma_num})
    ae.register_source('cn_tmpl', 'comma_numd: {thing|cn}')
    #print(ae.render('cn_tmpl', {'thing': 21000}))
    ae.register_source('tmpl', '{`{ok}thing`}')
    print(ae.render('tmpl', {'thing': 21000}))

    ae.register_source('tmpl2', '{test|s}')
    out = ae.render('tmpl2', {'test': ['<hi>'] * 10})
    print(out)

    ae.register_source('tmpl3', '{@iterate sort="desc" sort_key=1 key=lol}'
                       '{$0}: {$1}{~n}{/iterate}')
    out = ae.render('tmpl3', {'lol': {'uno': 1, 'dos': 2}})
    print(out)
    out = ae.render('tmpl3', {'lol': [(1, 2, 3), (4, 5, 6)]})
    print(out)


if __name__ == '__main__':
    _main()
