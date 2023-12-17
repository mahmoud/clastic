# -*- coding: utf-8 -*-

import itertools
from collections import defaultdict

from werkzeug.utils import cached_property
from werkzeug.wrappers import BaseResponse

from ..sinter import make_chain, get_arg_names, compile_code

_INNER_NAME = 'next'


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
    def requires(self):
        reqs = []
        for func_name in ('request', 'endpoint', 'render'):
            func = getattr(self, func_name, None)
            if func:
                reqs.extend(get_arg_names(func, True))
        unique_reqs = set(reqs)
        unique_reqs.discard('next')
        return list(unique_reqs)

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
            raise TypeError('expected %s.%s to be a function'
                            % (mw.name, f_name))
        if not get_arg_names(func)[0] == 'next':
            raise TypeError("middleware functions must take argument"
                            " 'next' as the first parameter (%s.%s)"
                            % (mw.name, f_name))
    return


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
        for arg in mw.endpoint_provides:
            provided_by[arg].append(mw)
        for arg in mw.render_provides:
            provided_by[arg].append(mw)

    conflicts = [(n, tuple(ps)) for (n, ps) in
                 provided_by.items() if len(ps) > 1]
    if conflicts:
        raise NameError('found conflicting provides: %r' % conflicts)
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
                                 'middleware %r' % mw.name)
        merged.append(mw)
    return merged


class DummyMiddleware(Middleware):
    def __init__(self, verbose=False):
        self.verbose = verbose

    def request(self, next, request):
        name = '%s (%s)' % (self.__class__.__name__, id(self))
        if self.verbose:
            print(name, '- handling', id(request))
        try:
            ret = next()
        except Exception as e:
            if self.verbose:
                print(name, '- uhoh:', repr(e))
            raise
        if self.verbose:
            print(name, '- hooray:', repr(ret))
        return ret


def make_middleware_chain(middlewares, endpoint, render, preprovided):
    """
    Expects de-duplicated and conflict-free middleware/endpoint/render
    functions.

    # TODO: better name to differentiate a compiled/chained stack from
    # the core functions themselves (endpoint/render)
    """
    _next_exc_msg = "argument 'next' reserved for middleware use only (%r)"
    if 'next' in get_arg_names(endpoint):
        raise NameError(_next_exc_msg % endpoint)
    if 'next' in get_arg_names(render):
        raise NameError(_next_exc_msg % render)

    req_avail = set(preprovided) - set(['next', 'context'])
    req_sigs = [(mw.request, mw.provides)
                for mw in middlewares if mw.request]
    req_funcs, req_provides = list(zip(*req_sigs)) or ((), ())
    req_all_provides = set(itertools.chain.from_iterable(req_provides))

    ep_avail = req_avail | req_all_provides
    ep_sigs = [(mw.endpoint, mw.endpoint_provides)
               for mw in middlewares if mw.endpoint]
    ep_funcs, ep_provides = list(zip(*ep_sigs)) or ((), ())
    ep_chain, ep_args, ep_unres = make_chain(ep_funcs,
                                             ep_provides,
                                             endpoint,
                                             ep_avail,
                                             _INNER_NAME)
    if ep_unres:
        raise NameError("unresolved endpoint middleware arguments: %r"
                        % list(ep_unres))

    rn_avail = ep_avail | set(['context'])
    rn_sigs = [(mw.render, mw.render_provides)
               for mw in middlewares if mw.render]
    rn_funcs, rn_provides = list(zip(*rn_sigs)) or ((), ())
    rn_chain, rn_args, rn_unres = make_chain(rn_funcs,
                                             rn_provides,
                                             render,
                                             rn_avail,
                                             _INNER_NAME)
    if rn_unres:
        raise NameError("unresolved render middleware arguments: %r"
                        % list(rn_unres))

    req_args = (ep_args | rn_args) - set(['context'])
    req_func = _create_request_inner(ep_chain,
                                     rn_chain,
                                     req_args,
                                     ep_args,
                                     rn_args)
    req_chain, req_chain_args, req_unres = make_chain(req_funcs,
                                                      req_provides,
                                                      req_func,
                                                      req_avail,
                                                      _INNER_NAME)
    if req_unres:
        raise NameError("unresolved request middleware arguments: %r"
                        % list(req_unres))
    return req_chain


_REQ_INNER_TMPL = \
'''
def process_request({all_args}):
    __traceback_hide__ = True
    context = endpoint({endpoint_args})
    if isinstance(context, BaseResponse):
        resp = context
    else:
        resp = render({render_args})
    return resp
'''


def _named_arg_str(args):
    return ', '.join([a + '=' + a for a in args])


def _create_request_inner(endpoint, render, all_args,
                          endpoint_args, render_args):
    all_args_str = ','.join(all_args)
    ep_args_str = _named_arg_str(endpoint_args)
    rn_args_str = _named_arg_str(render_args)

    code_str = _REQ_INNER_TMPL.format(all_args=all_args_str,
                                      endpoint_args=ep_args_str,
                                      render_args=rn_args_str)
    env = {'endpoint': endpoint, 'render': render, 'BaseResponse': BaseResponse}

    return compile_code(code_str, name='process_request', env=env)
