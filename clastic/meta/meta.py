from __future__ import unicode_literals

import os

from clastic.core import Application, RESERVED_ARGS
from clastic.sinter import getargspec
from clastic.render import json_response
from clastic.render import AshesRenderFactory

_CUR_DIR = os.path.dirname(__file__)


def create_app():
    routes = [('/', get_routes_info, 'base.html'),
              ('/json/', get_routes_info, json_response)]
    arf = AshesRenderFactory(_CUR_DIR)
    app = Application(routes, {}, arf)
    return app


def get_routes_info(_application):
    ret = {}
    app = _application
    route_infos = []
    for r in app.routes:
        r_info = {}
        r_info['url_rule'] = r.rule
        r_info['endpoint'] = get_endpoint_info(r)
        r_info['render'] = get_render_info(r)
        r_info['args'] = get_route_arg_info(r)
        route_infos.append(r_info)

    mw_infos = []
    for mw in app.middlewares:
        mw_infos.append(get_mw_info(mw))

    ret['routes'] = route_infos
    ret['middlewares'] = mw_infos
    return ret


def get_mw_info(mw):
    ret = {}
    ret['type_name'] = mw.__class__.__name__
    ret['provides'] = mw.provides
    ret['requires'] = mw.requires
    ret['repr'] = repr(mw)
    return ret


def get_endpoint_info(route):
    # TODO: callable object endpoints?
    ret = {}
    try:
        ret['name'] = route.endpoint.func_name
        ret['module_name'] = route.endpoint.__module__
    except:
        ret['name'] = repr(route.endpoint)
    return ret


def get_render_info(route):
    ret = {'type': None}
    if route._render_factory and not callable(route.render_arg):
        ret['type'] = route._render_factory.__class__.__name__
        ret['arg'] = route.render_arg
    else:
        try:
            ret['arg'] = route.render_arg.func_name
        except AttributeError:
            ret['arg'] = route.render_arg.__class__.__name__
    return ret


def get_route_arg_info(route):
    r_args, _, _, r_defaults = getargspec(route.endpoint)
    r_defaults = dict(reversed(zip(reversed(r_args),
                                   reversed(r_defaults or []))))
    arg_srcs = []
    for arg in r_args:
        arg_src = {'name': arg}
        source = None
        if arg in RESERVED_ARGS:
            source = 'builtin'
        elif arg in route.arguments:
            source = 'url'
        elif arg in route._resources:
            source = 'resources'
        else:
            for mw in route._middlewares:
                if arg in mw.provides:
                    source = 'middleware'
                    break
        if source is None:
            if arg in r_defaults:
                source = 'default'
        arg_src['source'] = source
        arg_srcs.append(arg_src)
    # TODO: trace to application if middleware/resource
    return arg_srcs


MetaApplication = create_app()

if __name__ == '__main__':
    MetaApplication.serve()
