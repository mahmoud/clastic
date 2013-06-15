# -*- coding: utf-8 -*-

import os
import sys
import socket
import platform
import datetime

IS_64BIT = sys.maxsize > 2 ** 32
try:
    from multiprocessing import cpu_count
    CPU_COUNT = cpu_count()
except:
    CPU_COUNT = None

try:
    import resource
except ImportError:
    resource = None

from core import Application, NullRoute, RESERVED_ARGS
from sinter import getargspec
from render import render_json, AshesRenderFactory
from static import StaticApplication

_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_ASSET_PATH = os.path.join(_CUR_PATH, '_clastic_assets')

# TODO: nominal SLA vs real/sampled SLA


def create_app():
    routes = [('/', get_all_meta_info, 'meta_base.html'),
              ('/clastic_assets/', StaticApplication(_ASSET_PATH)),
              ('/json/', get_all_meta_info, render_json)]
    resources = {'_meta_start_time': datetime.datetime.utcnow()}
    arf = AshesRenderFactory(_CUR_PATH)
    app = Application(routes, resources, arf)
    return app


def get_all_meta_info(_application, _meta_start_time):
    app = _application
    ret = {}
    ret['routes'] = get_route_infos(app)
    ret['resources'] = get_resource_info(app)
    ret['env'] = get_env_info()

    mw_infos = []
    for mw in app.middlewares:
        mw_infos.append(get_mw_info(mw))
    ret['middlewares'] = mw_infos

    ret['abs_start_time'] = str(_meta_start_time)
    ret['rel_start_time'] = _rel_datetime(_meta_start_time)
    return ret


def get_route_infos(_application):
    app = _application
    ret = []
    for r in app.routes:
        if isinstance(r, NullRoute):
            continue
        r_info = {}
        r_info['url_rule'] = r.rule
        r_info['endpoint'] = get_endpoint_info(r)
        r_info['render'] = get_render_info(r)
        r_info['args'] = get_route_arg_info(r)
        ret.append(r_info)
    return ret


def _trunc(str_val, length=70, trailer='...'):
    if len(str_val) > length:
        if trailer:
            str_val = str_val[:length - len(trailer)] + trailer
        else:
            str_val = str_val[:length]
    return str_val


def _rel_datetime(d, other=None):
    # TODO: add decimal rounding factor (default 0)
    if other is None:
        other = datetime.datetime.utcnow()
    diff = other - d
    s, days = diff.seconds, diff.days
    if days > 7 or days < 0:
        return d.strftime('%d %b %y')
    elif days == 1:
        return '1 day ago'
    elif days > 1:
        return '{0} days ago'.format(diff.days)
    elif s < 5:
        return 'just now'
    elif s < 60:
        return '{0} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{0} minutes ago'.format(s / 60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{0} hours ago'.format(s / 3600)


def get_env_info():
    ret = {}
    ret['proc'] = get_proc_info()
    ret['host'] = get_host_info()
    ret['pyvm'] = get_pyvm_info()
    return ret


def get_proc_info():
    ret = {}
    ret['pid'] = os.getpid()
    _user_t, _sys_t = os.times()[:2]
    ret['cpu_times'] = {'user_time': _user_t, 'sys_time': _sys_t}
    ret['cwd'] = os.getcwdu()
    ret['umask'] = os.umask(os.umask(2))  # have to set to get
    ret['umask_str'] = '{0:03o}'.format(ret['umask'])
    try:
        import getpass
        ret['owner'] = getpass.getuser()
    except:
        try:
            ret['owner'] = os.getuid()
        except:
            pass
    try:
        # unix-only
        ret['ppid'] = os.getppid()
        ret['pgid'] = os.getpgrp()
        # add 0 to get current nice
        # also, seems to return process group's nice level
        ret['niceness'] = os.nice(0)
    except AttributeError:
        pass
    ret['rusage'] = get_rusage_dict()
    ret['rlimit'] = get_rlimit_dict()
    return ret


def get_rlimit_dict():
    ret = {}
    if not resource:
        return ret
    rname_val = [(rn[7:].lower(), val) for rn, val in resource.__dict__.items()
                 if rn.startswith('RLIMIT_')]
    for rn, val in rname_val:
        ret[rn] = resource.getrlimit(val)
    return ret


# TODO: byte order, path, prefix
def get_host_info():
    ret = {}
    ret['hostname'] = socket.gethostname()
    ret['hostfqdn'] = socket.getfqdn()
    ret['uname'] = platform.uname()
    ret['cpu_count'] = CPU_COUNT
    ret['platform'] = platform.platform()
    ret['platform_terse'] = platform.platform(terse=True)
    try:
        ret['load_avgs'] = os.getloadavg()
    except AttributeError:
        pass
    return ret


def get_rusage_dict(children=False):
    # TODO:
    # number of child processes?
    # page size
    # difference between a page out and a major fault?
    # NOTE: values commented with an * are untracked on Linux
    if not resource:
        return {}
    who = resource.RUSAGE_SELF
    if children:
        who = resource.RUSAGE_CHILDREN
    rr = resource.getrusage(who)
    ret = {'cpu_times': {'user_time': rr.ru_utime,
                         'sys_time': rr.ru_stime},
           'memory': {'max_rss': rr.ru_maxrss,
                      'shared_rss': rr.ru_ixrss,    # *
                      'unshared_rss': rr.ru_idrss,  # *
                      'stack_rss': rr.ru_isrss},    # *
           'page_faults': {'minor_faults': rr.ru_minflt,
                           'major_faults': rr.ru_majflt,
                           'page_outs': rr.ru_nswap},  # *
           'blocking_io': {'input_ops': rr.ru_inblock,
                           'output_ops': rr.ru_oublock},
           'messages': {'sent': rr.ru_msgsnd,  # *
                        'received': rr.ru_msgrcv},  # *
           'signals': {'received': rr.ru_nsignals},  # *
           'ctx_switches': {'voluntary': rr.ru_nvcsw,
                            'involuntary': rr.ru_nivcsw}}
    return ret


def get_pyvm_info():

    ret = {}
    ret['executable'] = sys.executable
    ret['is_64bit'] = IS_64BIT
    try:
        ret['active_thread_count'] = len(sys._current_frames())
    except:
        ret['active_thread_count'] = None
    ret['recursion_limit'] = sys.getrecursionlimit()  # TODO: max_stack_depth?
    ret['gc'] = get_gc_info()
    return ret


def get_gc_info():
    import gc
    ret = {}
    ret['is_enabled'] = gc.isenabled()
    ret['thresholds'] = gc.get_threshold()
    ret['counts'] = gc.get_count()
    ret['obj_count'] = len(gc.get_objects())
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
