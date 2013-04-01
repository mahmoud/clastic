from __future__ import unicode_literals

import os
import datetime

from core import Application, RESERVED_ARGS
from sinter import getargspec
from render import json_response, AshesRenderFactory


_CUR_DIR = os.path.dirname(__file__)


def create_app():
    routes = [('/', get_routes_info, 'meta_base.html'),
              ('/json/', get_routes_info, json_response)]
    resources = {'_meta_start_time': datetime.datetime.utcnow()}
    arf = AshesRenderFactory(_CUR_DIR)
    app = Application(routes, resources, arf)
    return app


def get_routes_info(_application, _meta_start_time):
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

    ret['abs_start_time'] = str(_meta_start_time)
    ret['rel_start_time'] = _rel_datetime(_meta_start_time)
    ret['routes'] = route_infos
    ret['middlewares'] = mw_infos
    ret['resources'] = get_resource_info(app)
    ret['env'] = get_env_info()
    return ret


def _trunc(str_val, length=70, trailer='...'):
    if len(str_val) > length:
        if trailer:
            str_val = str_val[:length - len(trailer)] + trailer
        else:
            str_val = str_val[:length]
    return str_val


def _rel_datetime(d, other=None):
    if other is None:
        other = datetime.datetime.utcnow()
    diff = other - d
    s, days = diff.seconds, diff.days
    if days > 7 or days < 0:
        return d.strftime('%d %b %y')
    elif days == 1:
        return '1 day ago'
    elif days > 1:
        return '{} days ago'.format(diff.days)
    elif s < 5:
        return 'just now'
    elif s < 60:
        return '{} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{} minutes ago'.format(s/60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(s/3600)


def get_env_info():
    import os
    ret = {}
    ret['pid'] = os.getpid()
    ret['times'] = os.times()[:2]
    try:
        ret['load_avgs'] = os.getloadavg()
    except:
        ret['load_avgs'] = (None, None, None)
    return ret


def get_resource_info(_application):
    ret = []
    for key, val in _application.resources.items():
        trunc_val = _trunc(repr(val))
        ret.append({'key': key, 'value': trunc_val})
    return ret


def get_mw_info(mw):
    # TODO: what to do about render and endpoint provides?
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
