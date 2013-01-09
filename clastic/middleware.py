import itertools
from collections import defaultdict, Mapping, Iterable

from werkzeug.utils import cached_property
from werkzeug.wrappers import Response  # TODO: remove dependency

from sinter import make_chain, get_arg_names, _VERBOSE


class Middleware(object):
    unique = True
    reorderable = True
    provides = ()
    endpoint_provides = ()
    render_provides = ()

    request = None
    endpoint = None
    render = None

    @property
    def name(self):
        return self.__class__.__name__

    def __eq__(self, other):
        return type(self) == type(other)

    def __ne__(self, other):
        return type(self) != type(other)

    @cached_property
    def requirements(self):
        reqs = []
        for func_name in ('request', 'endpoint', 'render'):
            func = getattr(self, func_name, None)
            if func:
                reqs.extend(get_arg_names(func, True))
        return set(reqs)

    @cached_property
    def arguments(self):
        args = []
        for func_name in ('request', 'endpoint', 'render'):
            func = getattr(self, func_name, None)
            if func:
                args.extend(get_arg_names(func))
        return set(args)


def check_middleware(mw):
    for f_name in ('request', 'endpoint', 'render'):
        func = getattr(mw, f_name, None)
        if not func:
            continue
        if not callable(func):
            raise TypeError('expected middleware.' + f_name + ' to be a function')
        if not get_arg_names(func)[0] == 'next':
            raise TypeError("middleware functions must take a first parameter 'next'")


def check_middlewares(middlewares, args_dict=None):
    args_dict = args_dict or {}

    provided_by = defaultdict(list)
    for source, arg_list in args_dict.items():
        for arg_name in arg_list:
            provided_by[arg_name].append(source)

    for mw in middlewares:
        check_middleware(mw)
        for arg in mw.provides:
            provided_by[arg].append(mw)

    conflicts = [(n, tuple(ps)) for (n, ps) in provided_by.items() if len(ps) > 1]
    if conflicts:
        raise NameError('found conflicting provides: ' + repr(conflicts))
    return True


def merge_middlewares(old, new):
    # TODO: since duplicate provides aren't allowed
    # an error needs to be raised if a middleware is
    # set to non-unique and has provides params
    old = list(old)
    merged = list(new)
    for mw in old:
        if mw.unique and mw in merged:
            if mw.reorderable:
                continue
            else:
                raise ValueError('multiple inclusion of unique '
                                 'middleware ' + mw.name)
        merged.append(mw)
    return merged


class DummyMiddleware(Middleware):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def request(self, next, request):
        name = '%s (%s)' % (self.__class__.__name__, id(self))
        if self.verbose:
            print name, '- handling', id(request)
        try:
            ret = next()
        except Exception as e:
            if self.verbose:
                print name, '- uhoh:', repr(e)
            raise
        if self.verbose:
            print name, '- hooray:', repr(ret)
        return ret


def make_middleware_chain(middlewares, endpoint, render, preprovided):
    """
    Expects de-duplicated and conflict-free
    middleware/endpoint/render functions.
    """
    req_avail = set(preprovided) - set(['next'])
    req_sigs = [(mw.request, mw.provides)
                for mw in middlewares if mw.request]
    req_funcs, req_provides = zip(*req_sigs) or ((), ())
    req_all_provides = set(itertools.chain.from_iterable(req_provides))

    ep_avail = req_avail | req_all_provides
    ep_sigs = [(mw.endpoint, mw.endpoint_provides)
               for mw in middlewares if mw.endpoint]
    ep_funcs, ep_provides = zip(*ep_sigs) or ((), ())
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
    rn_chain, rn_args, rn_unres = make_chain(rn_funcs,
                                             rn_provides,
                                             render,
                                             rn_avail)
    if rn_unres:
        raise NameError("unresolved render middleware arguments: %r"
                        % rn_unres)

    req_args = (ep_args | rn_args) - set(['context'])
    req_func = _create_request_inner(ep_chain,
                                     rn_chain,
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
    return ','.join([a + '=' + a for a in args])


def _create_request_inner(endpoint, render, all_args,
                          endpoint_args, render_args,
                          verbose=_VERBOSE):
    all_args_str = ','.join(all_args)
    ep_args_str = _named_arg_str(endpoint_args)
    rn_args_str = _named_arg_str(render_args)

    code_str = _REQ_INNER_TMPL.format(all_args=all_args_str,
                                      endpoint_args=ep_args_str,
                                      render_args=rn_args_str)
    if verbose:
        print code_str  # pragma: nocover
    d = {'endpoint': endpoint, 'render': render, 'Response': Response}

    exec compile(code_str, '<string>', 'single') in d

    return d['process_request']


class GetParamMiddleware(Middleware):
    def __init__(self, params=None):
        # TODO: defaults?
        if isinstance(params, Mapping):
            self.params = params
        elif isinstance(params, basestring):
            self.params = {params: unicode}
        elif isinstance(params, Iterable):
            self.params = dict([(p, unicode) for p in params])
        else:
            raise TypeError('expected a string, dict, mapping, or iterable.')
        if not all([isinstance(v, type) for v in self.params.values()]):
            raise TypeError('param mapping values must be a valid type')
        self.provides = tuple(self.params.iterkeys())

    def request(self, next, request):
        kwargs = {}
        for p_name, p_type in self.params.items():
            kwargs[p_name] = request.args.get(p_name, None, p_type)
        return next(**kwargs)
