import types
import inspect
import itertools

from werkzeug.wrappers import Response  # TODO: remove dependency

VERBOSE = False

def getargspec(f):
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
    if defaults:
        defaults = dict(reversed(zip(reversed(arg_names), reversed(defaults))))
    else:
        defaults = {}
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
    #args, opts = getargspec(funcs[0])
    next_args = getargspec(funcs[0])[0]
    print funcs[0], next_args  # DEBUG
    next_args = ','.join([a+'='+a for a in next_args if a in params_sofar])
    return '   '*level +'def next('+','.join(params[0])+'):\n'+\
        build_chain_str(funcs[1:], params[1:], params_sofar, level+1)+\
        '   '*(level+1)+'return funcs['+str(level)+']('+next_args+')\n'


def compile_chain(funcs, params, verbose=VERBOSE):
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
    print 'args:', args, '- reqs:', reqs, '- opts:', opts, '- provided:', preprovided
    print 'unresolved:', unresolved
    chain = compile_chain(funcs + [final_func],
                          [args] + provides)
    return chain, set(args), set(unresolved)


def make_middleware_chain(middlewares, endpoint, render, preprovided):
    """
    Expects de-duplicated and conflict-free
    middleware/endpoint/render functions.
    """
    req_avail = set(preprovided) - set(['next'])
    req_sigs = [(mw.request, mw.provides)
                for mw in middlewares if mw.request]
    req_funcs, req_provides = zip(*req_sigs) or ((), ())
    #import pdb;pdb.set_trace()
    req_all_provides = set(itertools.chain.from_iterable(req_provides))

    ep_avail = req_avail | req_all_provides
    ep_sigs = [(mw.endpoint, mw.endpoint_provides)
               for mw in middlewares if mw.endpoint]
    ep_funcs, ep_provides = zip(*ep_sigs) or ((), ())
    #ep_all_provides = set(itertools.chain.from_iterable(ep_provides))
    ep_chain, ep_args, ep_unres = make_chain(ep_funcs,
                                             ep_provides,
                                             endpoint,
                                             ep_avail)
    if ep_unres:
        raise NameError("unresolved endpoint middleware arguments: %r"
                        % ep_unres)

    rn_avail = ep_avail | set(['context'])
    rn_sigs = [(mw.render, mw.render_provides)
               for mw in middlewares if mw.render]
    rn_funcs, rn_provides = zip(*rn_sigs) or ((), ())
    #rn_all_provides = set(itertools.chain.from_iterable(rn_provides))
    rn_chain, rn_args, rn_unres = make_chain(rn_funcs,
                                             rn_provides,
                                             render,
                                             rn_avail)
    if rn_unres:
        raise NameError("unresolved render middleware arguments: %r"
                        % rn_unres)

    req_args = (ep_args | rn_args) - set(['context'])
    print 'req_args:', req_args
    req_func = _create_request_inner(endpoint,
                                     render,
                                     req_args,
                                     ep_args,
                                     rn_args)
    req_chain, req_chain_args, req_unres = make_chain(req_funcs,
                                                      req_provides,
                                                      req_func,
                                                      req_avail)
    if req_unres:
        raise NameError("unresolved request middleware arguments: %r"
                        % req_unres)
    return req_chain


_REQ_INNER_TMPL = \
'''
def process_request({all_args}):
    context = endpoint({endpoint_args})
    if isinstance(context, Response):
        resp = context
    else:
        resp = render({render_args})
    return resp
'''


def _named_arg_str(args):
    return ','.join([a+'='+a for a in args])


def _create_request_inner(endpoint, render, all_args,
                          endpoint_args, render_args,
                          verbose=VERBOSE):
    all_args_str = ','.join(all_args)
    ep_args_str = _named_arg_str(endpoint_args)
    rn_args_str = _named_arg_str(render_args)

    code_str = _REQ_INNER_TMPL.format(all_args=all_args_str,
                                      endpoint_args=ep_args_str,
                                      render_args=rn_args_str)
    if verbose:
        print code_str
    d = {'endpoint':endpoint, 'render':render, 'Response':Response}

    exec compile(code_str, '<string>', 'single') in d

    return d['process_request']
