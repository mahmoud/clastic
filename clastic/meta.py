# -*- coding: utf-8 -*-

import os
import sys
import socket
import platform
import datetime
import collections

IS_64BIT = sys.maxsize > 2 ** 32
try:
    from multiprocessing import cpu_count
    CPU_COUNT = cpu_count()
except:
    CPU_COUNT = None

HAVE_READLINE = True
try:
    import readline
except:
    HAVE_READLINE = False

try:
    import resource
except ImportError:
    resource = None

from application import Application, NullRoute, RESERVED_ARGS
from sinter import getargspec, inject
from render import render_json, AshesRenderFactory
from static import StaticApplication
from utils import bytes2human

from middleware.url import ScriptRootMiddleware
from middleware.context import SimpleContextProcessor


_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_ASSET_PATH = os.path.join(_CUR_PATH, '_clastic_assets')

# TODO: nominal SLA vs real/sampled SLA

DEFAULT_PAGE_TITLE = 'Clastic'


def create_app(page_title=DEFAULT_PAGE_TITLE):
    routes = [('/', get_all_meta_info, 'meta_base.html'),
              ('/clastic_assets/', StaticApplication(_ASSET_PATH)),
              ('/json/', get_all_meta_info, render_json)]
    resources = {'_meta_start_time': datetime.datetime.utcnow(),
                 'page_title': page_title}
    arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
    middlewares = [ScriptRootMiddleware(),
                   SimpleContextProcessor('script_root')]
    app = Application(routes, resources, middlewares, arf)
    return app


def get_all_meta_info(_application, _meta_start_time, page_title):
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
    ret['page_title'] = page_title
    return ret


def get_route_infos(_application):
    app = _application
    ret = []
    for r in app.routes:
        if isinstance(r, NullRoute):
            continue
        r_info = {}
        r_info['url_pattern'] = r.pattern
        r_info['url_regex_pattern'] = r.regex.pattern
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
    max_rss_human = bytes2human(rr.ru_maxrss * 1024, ndigits=1)

    ret = {'cpu_times': {'user_time': rr.ru_utime,
                         'sys_time': rr.ru_stime},
           'memory': {'max_rss_human': max_rss_human,
                      'max_rss': rr.ru_maxrss,
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
    ret['version'] = sys.version
    ret['version_info'] = list(sys.version_info)
    ret['have_ucs4'] = getattr(sys, 'maxunicode', 0) > 65536
    ret['have_readline'] = HAVE_READLINE
    try:
        ret['active_thread_count'] = len(sys._current_frames())
    except:
        ret['active_thread_count'] = None
    ret['recursion_limit'] = sys.getrecursionlimit()  # TODO: max_stack_depth?
    try:
        ret['gc'] = get_gc_info()
    except:
        pass
    ret['check_interval'] = sys.getcheckinterval()
    return ret


def get_gc_info():
    import gc
    ret = {}
    ret['is_enabled'] = gc.isenabled()
    ret['thresholds'] = gc.get_threshold()
    try:
        ret['counts'] = gc.get_count()
    except:
        pass
    try:
        ret['obj_count'] = len(gc.get_objects())
    except:
        pass
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
    render_arg = route.render_arg
    if route._render_factory and not callable(render_arg):
        ret['type'] = route._render_factory.__class__.__name__
        ret['arg'] = render_arg
    elif render_arg is None:
        ret['arg'] = None
    else:
        try:
            ret['arg'] = render_arg.func_name
        except AttributeError:
            ret['arg'] = render_arg.__class__.__name__
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
        elif arg in route.path_args:
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


class MetaPeripheral(object):
    title = 'Clastic MetaPeripheral'
    group_key = 'mp'

    def get_general_items(self):
        "Returns list of 2-tuples to appear in the general section table"
        return []

    def get_context(self):
        return {}

    def render_main_page_html(self, context):
        return None

    def get_extra_routes(self):
        return []


class BasicPeripheral(MetaPeripheral):
    title = 'Basic Peripheral'
    group_key = 'basic'

    def get_context(self, _meta_application):
        start_time = _meta_application.resources['_meta_start_time']
        return {'abs_start_time': str(start_time),
                'rel_start_time': _rel_datetime(start_time)}

    def get_general_items(self, context):
        return [('Start time', (context['rel_start_time'],
                                context['abs_start_time']))]


class EnvironmentPeripheral(MetaPeripheral):
    title = 'Environment'
    group_key = 'env'

    def __init__(self):
        arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self.loaded_template = arf.env.load('meta_env_section.html')

    get_context = staticmethod(get_env_info)

    def get_general_items(self, context):
        ret = [('PID', context['proc']['pid'])]
        try:
            load_avgs = context['host']['load_avgs']
            if load_avgs:
                ret.append(('Load averages', repr(load_avgs)))
        except KeyError:
            pass
        return ret

    def render_main_page_html(self, context):
        return self.loaded_template.render(context)


class RoutePeripheral(MetaPeripheral):
    title = 'Routes'
    group_key = 'app'

    def __init__(self):
        arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self.loaded_template = arf.env.load('meta_route_section.html')

    def get_context(self, _application):
        return {'routes': get_route_infos(_application)}

    def render_main_page_html(self, context):
        return self.loaded_template.render(context)


class MiddlewarePeripheral(MetaPeripheral):
    title = 'Application-wide Middlewares'
    group_key = 'app'

    def __init__(self):
        arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self.loaded_template = arf.env.load('meta_mw_section.html')

    def get_context(self, _application):
        return {'middlewares': get_mw_info(_application)}

    def render_main_page_html(self, context):
        return self.loaded_template.render(context)


class ResourcePeripheral(MetaPeripheral):
    title = 'Application Resources'
    group_key = 'app'

    def __init__(self):
        arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self.loaded_template = arf.env.load('meta_resource_section.html')

    def get_context(self, _application):
        return {'resources': get_resource_info(_application)}

    def render_main_page_html(self, context):
        return self.loaded_template.render(context)


class MetaApplication2(Application):
    def __init__(self, peripherals=None, page_title=DEFAULT_PAGE_TITLE):
        self.page_title = page_title
        self.peripherals = peripherals or []

        self._arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self._main_page_render = self._arf('meta2_base.html')
        routes = [('/', self.get_main, self.render_main_page_html),
                  ('/clastic_assets/', StaticApplication(_ASSET_PATH)),
                  ('/json/', self.get_main, render_json)]
        for peri in self.peripherals:
            routes.extend(peri.get_extra_routes())
        resources = {'_meta_start_time': datetime.datetime.utcnow(),
                     'page_title': page_title}

        mwares = [ScriptRootMiddleware(),
                  SimpleContextProcessor('script_root')]
        super(MetaApplication2, self).__init__(routes, resources, mwares)

    def get_main(self, request, _application, _route):
        full_ctx = {'page_title': self.page_title}
        kwargs = {'request': request,
                  '_route': _route,
                  '_application': _application,
                  '_meta_application': self}
        for peri in self.peripherals:
            try:
                peri_ctx = inject(peri.get_context, kwargs)
            except Exception as e:
                peri_ctx = {'exc_content': repr(e)}
            full_ctx.setdefault(peri.group_key, {}).update(peri_ctx)
        return full_ctx

    def render_main_page_html(self, context):
        context['sections'] = []
        general_items = context['general'] = []

        for peri in self.peripherals:
            cur = {'title': peri.title,
                   'group_key': peri.group_key}
            try:
                kwargs = {'context': context[peri.group_key]}
                content = inject(peri.render_main_page_html, kwargs)
                cur['content'] = content
            except Exception as e:
                cur['exc_content'] = repr(e)
            try:
                cur_general_items = inject(peri.get_general_items, kwargs)
                cur_general_items = _process_items(cur_general_items)
            except Exception as e:
                cur_general_items = []
            context['sections'].append(cur)
            general_items.extend(cur_general_items)
        return self._main_page_render(context)


def _process_items(all_items):
    """ Really, each key/value/key detail/value detail should have a
    human readable form and a machine readable form. That's a lot of
    keys, should probably do that later.
    """
    ret = []
    for item in all_items:
        cur = {}
        try:
            key, value = item
        except:
            try:
                key, value = item[0], item[1:]
            except:
                value = ''
                try:
                    key = repr(item)
                except:
                    key = 'unreprable object %s' % object.__repr__(key)
        if isinstance(key, basestring):
            cur['key'] = key
        else:
            try:
                cur['key'] = unicode(key[0])
                cur['key_detail'] = unicode(key[1])
            except:
                cur['key'] = unicode(key)
        if isinstance(value, basestring):
            cur['value'] = value
        else:
            try:
                cur['value'] = unicode(value[0])
                cur['value_detail'] = unicode(value[1])
            except:
                cur['value'] = str(value)
        ret.append(cur)
    return ret


"""
* register template, get keys
"""


if __name__ == '__main__':
    pass
