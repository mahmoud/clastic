import types
import inspect

_VERBOSE = False


def getargspec(f):
    # TODO: support partials
    if not inspect.isfunction(f) and not inspect.ismethod(f) \
            and hasattr(f, '__call__'):
        f = f.__call__  # callable objects
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
    arg_names, _, _, defaults = getargspec(f)
    defaults = dict(reversed(zip(reversed(arg_names),
                                 reversed(defaults or []))))
    args = {}
    for n in arg_names:
        if n in injectables:
            args[n] = injectables[n]
        else:
            args[n] = defaults[n]
    return f(**args)


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
        # keep track of defaults so that e.g. endpoint default param can pick up
        # request injected/provided param
        required_sofar |= set(undefaulted) - provided_sofar
        provided_sofar.update(p)

    return required_sofar, optional_sofar


#funcs[0] = function to call
#params[0] = parameters to take
def build_chain_str(funcs, params, params_sofar=None, level=0):
    if not funcs:
        return ''  # stopping case
    if params_sofar is None:
        params_sofar = set(['next'])
    params_sofar.update(params[0])
    next_args = getargspec(funcs[0])[0]
    next_args = ','.join([a+'='+a for a in next_args if a in params_sofar])
    return '   '*level +'def next('+','.join(params[0])+'):\n'+\
        build_chain_str(funcs[1:], params[1:], params_sofar, level+1)+\
        '   '*(level+1)+'return funcs['+str(level)+']('+next_args+')\n'


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
