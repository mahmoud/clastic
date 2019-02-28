# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import types
import inspect
import hashlib
import linecache

from boltons import iterutils
from boltons.strutils import camel2under
from boltons.funcutils import FunctionBuilder

PY3 = (sys.version_info[0] == 3)
_VERBOSE = False
_INDENT = '    '


def get_fb(f, drop_self=True):
    # TODO: support partials
    if not (inspect.isfunction(f) or inspect.ismethod(f) or \
            inspect.isbuiltin(f)) and hasattr(f, '__call__'):
        if isinstance(getattr(f, '_sinter_fb', None), FunctionBuilder):
            return f._sinter_fb
        f = f.__call__  # callable objects

    if isinstance(getattr(f, '_sinter_fb', None), FunctionBuilder):
        return f._sinter_fb  # we'll take your word for it; good luck, lil buddy.

    ret = FunctionBuilder.from_func(f)

    if not all([isinstance(a, str) for a in ret.args]):
        raise TypeError('does not support anonymous tuple arguments'
                        ' or any other strange args for that matter.')
    if drop_self and isinstance(f, types.MethodType):
        ret.args = ret.args[1:]  # discard "self" on methods
    return ret


def get_arg_names(f, only_required=False):
    fb = get_fb(f)

    return fb.get_arg_names(only_required=only_required)


def inject(f, injectables):
    __traceback_hide__ = True  # TODO

    fb = get_fb(f)

    all_kwargs = fb.get_defaults_dict()
    all_kwargs.update(injectables)

    if fb.varkw:
        return f(**all_kwargs)

    kwargs = dict([(k, v) for k, v in all_kwargs.items() if k in fb.get_arg_names()])
    return f(**kwargs)


def get_func_name(obj, with_module=False):
    if not callable(obj):
        raise TypeError('expected a callable object')
    ret = []
    if with_module and obj.__module__:
        ret.append(obj.__module__)
    if isinstance(obj, types.MethodType):
        ret.append(obj.im_class.__name__)
        obj = obj.im_func
    func_name = getattr(obj, 'func_name', None)
    if not func_name:
        func_name = repr(obj)
    ret.append(func_name)
    return '.'.join(ret)


# TODO: turn the following into an object (keeps inner_name easier to
# track, as well as better handling of state the func_aliaser will
# need

def chain_argspec(func_list, provides, inner_name):
    provided_sofar = set([inner_name])  # the inner function name is an extremely special case
    optional_sofar = set()
    required_sofar = set()
    for f, p in zip(func_list, provides):
        # middlewares can default the same parameter to different values;
        # can't properly keep track of default values
        fb = get_fb(f)
        arg_names = fb.get_arg_names()
        defaults_dict = fb.get_defaults_dict()

        defaulted, undefaulted = iterutils.partition(arg_names, key=defaults_dict.__contains__)

        optional_sofar.update(defaulted)
        # keep track of defaults so that e.g. endpoint default param
        # can pick up request injected/provided param
        required_sofar |= set(undefaulted) - provided_sofar
        provided_sofar.update(p)

    return required_sofar, optional_sofar


#funcs[0] = function to call
#params[0] = parameters to take
def build_chain_str(funcs, params, inner_name, params_sofar=None, level=0,
                    func_aliaser=None, func_names=None):
    if not funcs:
        return ''  # stopping case
    if params_sofar is None:
        params_sofar = set([inner_name])

    params_sofar.update(params[0])
    inner_args = get_fb(funcs[0]).args
    inner_arg_dict = dict([(a, a) for a in inner_args])
    inner_arg_items = sorted(inner_arg_dict.items())
    inner_args = ', '.join(['%s=%s' % kv for kv in inner_arg_items
                           if kv[0] in params_sofar])
    outer_indent = _INDENT * level
    inner_indent = outer_indent + _INDENT
    outer_arg_str = ', '.join(params[0])
    def_str = '%sdef %s(%s):\n' % (outer_indent, inner_name, outer_arg_str)
    body_str = build_chain_str(funcs[1:], params[1:], inner_name, params_sofar, level + 1)
    #func_name = get_func_name(funcs[0])
    #func_alias = get_inner_func_alias(funcs[0])
    htb_str = '%s__traceback_hide__ = True\n' % (inner_indent,)
    return_str = '%sreturn funcs[%s](%s)\n' % (inner_indent, level, inner_args)
    return ''.join([def_str, body_str, htb_str + return_str])


def compile_chain(funcs, params, inner_name, verbose=_VERBOSE):
    call_str = build_chain_str(funcs, params, inner_name)
    code_hash = hashlib.sha1(call_str.encode('utf8')).hexdigest()[:16]
    unique_filename = "<sinter generated %s chain %s>" % (inner_name, code_hash)
    code = compile(call_str, unique_filename, 'single')
    if verbose:
        print(call_str)
    env = {'funcs': funcs}
    if PY3:
        exec(code, env)
    else:
        exec("exec code in env")

    linecache.cache[unique_filename] = (
        len(call_str),
        None,
        call_str.splitlines(True),
        unique_filename,
    )

    return env[inner_name]


def make_chain(funcs, provides, final_func, preprovided, inner_name):
    funcs = list(funcs)
    provides = list(provides)
    preprovided = set(preprovided)
    reqs, opts = chain_argspec(funcs + [final_func],
                               provides + [()], inner_name)

    unresolved = tuple(reqs - preprovided)
    args = reqs | (preprovided & opts)
    chain = compile_chain(funcs + [final_func],
                          [args] + provides, inner_name)
    return chain, set(args), set(unresolved)


def get_inner_func_alias(func, inner_name, func_names=None):
    if func_names is None:
        func_names = set()
    func_name = get_func_name(func)
    func_alias = camel2under(func_name.replace('.', '__'))
    func_alias = func_alias.replace('middleware', 'mw')
    while func_alias in func_names:
        try:
            head, _, tail = func_alias.rpartition('_')
            cur_count = int(tail)
            func_alias = '%s_%s' % (head, cur_count + 1)
        except Exception:
            func_alias = func_alias + '_2'
    return '%s_%s' % (inner_name, func_alias)
