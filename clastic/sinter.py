# -*- coding: utf-8 -*-

import re
import types
import inspect
from inspect import ArgSpec

_VERBOSE = False
_INDENT = '    '


def getargspec(f):
    # TODO: support partials
    if not (inspect.isfunction(f) or inspect.ismethod(f) or \
            inspect.isbuiltin(f)) and hasattr(f, '__call__'):
        if isinstance(getattr(f, '_argspec', None), ArgSpec):
            return f._argspec
        f = f.__call__  # callable objects

    if isinstance(getattr(f, '_argspec', None), ArgSpec):
        return f._argspec  # we'll take your word for it; good luck, lil buddy.

    ret = inspect.getargspec(f)

    if not all([isinstance(a, basestring) for a in ret.args]):
        raise TypeError('does not support anonymous tuple arguments '
                        'or any other strange args for that matter.')
    if isinstance(f, types.MethodType):
        ret = ret._replace(args=ret.args[1:])  # throw away "self"
    return ret


def get_arg_names(f, only_required=False):
    arg_names, _, _, defaults = getargspec(f)

    if only_required and defaults:
        arg_names = arg_names[:-len(defaults)]

    return tuple(arg_names)


def inject(f, injectables):
    __traceback_hide__ = True  # TODO
    arg_names, _, kw_name, defaults = getargspec(f)
    defaults = dict(reversed(zip(reversed(arg_names),
                                 reversed(defaults or []))))
    all_kwargs = dict(defaults)
    all_kwargs.update(injectables)
    if kw_name:
        return f(**all_kwargs)

    kwargs = dict([(k, v) for k, v in all_kwargs.items() if k in arg_names])
    return f(**kwargs)


def chain_argspec(func_list, provides):
    provided_sofar = set(['next'])  # 'next' is an extremely special case
    optional_sofar = set()
    required_sofar = set()
    for f, p in zip(func_list, provides):
        # middlewares can default the same parameter to different values;
        # can't properly keep track of default values
        arg_names, _, _, defaults = getargspec(f)

        def_offs = -len(defaults) if defaults else None
        undefaulted, defaulted = arg_names[:def_offs], arg_names[def_offs:]
        optional_sofar.update(defaulted)
        # keep track of defaults so that e.g. endpoint default param
        # can pick up request injected/provided param
        required_sofar |= set(undefaulted) - provided_sofar
        provided_sofar.update(p)

    return required_sofar, optional_sofar


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


#funcs[0] = function to call
#params[0] = parameters to take
def build_chain_str(funcs, params, params_sofar=None, level=0,
                    func_aliaser=None, func_names=None):
    if not funcs:
        return ''  # stopping case
    if params_sofar is None:
        params_sofar = set(['next'])

    params_sofar.update(params[0])
    next_args = getargspec(funcs[0]).args
    next_arg_dict = dict([(a, a) for a in next_args])
    next_arg_items = sorted(next_arg_dict.iteritems())
    next_args = ', '.join(['%s=%s' % kv for kv in next_arg_items
                           if kv[0] in params_sofar])
    outer_indent = _INDENT * level
    inner_indent = outer_indent + _INDENT
    outer_arg_str = ', '.join(params[0])
    def_str = '%sdef next(%s):\n' % (outer_indent, outer_arg_str)
    body_str = build_chain_str(funcs[1:], params[1:], params_sofar, level + 1)
    #func_name = get_func_name(funcs[0])
    #func_alias = get_next_func_alias(funcs[0])
    htb_str = '%s__traceback_hide__ = True\n' % (inner_indent,)
    return_str = '%sreturn funcs[%s](%s)\n' % (inner_indent, level, next_args)
    return ''.join([def_str, body_str, htb_str + return_str])


def compile_chain(funcs, params, verbose=_VERBOSE):
    call_str = build_chain_str(funcs, params)
    code = compile(call_str, '<string>', 'single')
    if verbose:
        print call_str
    d = {'funcs': funcs}
    exec code in d
    return d['next']


def make_chain(funcs, provides, final_func, preprovided):
    funcs = list(funcs)
    provides = list(provides)
    preprovided = set(preprovided)
    reqs, opts = chain_argspec(funcs + [final_func],
                               provides + [()])

    unresolved = tuple(reqs - preprovided)
    args = reqs | (preprovided & opts)
    chain = compile_chain(funcs + [final_func],
                          [args] + provides)
    return chain, set(args), set(unresolved)


_camel2under_re = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def camel2under(camel_string):
    return _camel2under_re.sub(r'_\1', camel_string).lower()


def get_next_func_alias(func, func_names=None):
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
        except:
            func_alias = func_alias + '_2'
    return 'next_' + func_alias
