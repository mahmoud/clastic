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

HAVE_READLINE = True
try:
    import readline
except:
    HAVE_READLINE = False

try:
    import resource
except ImportError:
    resource = None

try:
    import sysconfig
except ImportError:
    try:
        from distutils import sysconfig
    except ImportError:
        sysconfig = None


from application import Application, NullRoute, RESERVED_ARGS
from sinter import getargspec, inject
from render import render_json, AshesRenderFactory
from static import StaticApplication
from utils import bytes2human, rel_datetime

from middleware.url import ScriptRootMiddleware
from middleware.context import SimpleContextProcessor


_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_ASSET_PATH = os.path.join(_CUR_PATH, '_clastic_assets')

DEFAULT_PAGE_TITLE = 'Clastic'


def _trunc(str_val, length=70, trailer='...'):
    if len(str_val) > length:
        if trailer:
            str_val = str_val[:length - len(trailer)] + trailer
        else:
            str_val = str_val[:length]
    return str_val


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


def get_rlimit_dict():
    ret = {}
    if not resource:
        return ret
    rname_val = [(rn[7:].lower(), val) for rn, val in resource.__dict__.items()
                 if rn.startswith('RLIMIT_')]
    for rn, val in rname_val:
        ret[rn] = resource.getrlimit(val)
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
    if sys.platform == 'darwin':
        rss_bytes = rr.ru_maxrss  # darwin breaks posix
    else:
        rss_bytes = rr.ru_maxrss * 1024
    max_rss_human = bytes2human(rss_bytes, ndigits=1)

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
    ret['rlimit'] = get_rlimit_dict()
    return ret


def get_pyvm_info():
    ret = {}
    ret['executable'] = sys.executable
    ret['is_64bit'] = IS_64BIT
    ret['version'] = sys.version
    ret['compiler'] = platform.python_compiler()
    ret['build_date'] = platform.python_build()[1]
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


def get_mw_infos(_application):
    # TODO: what to do about render and endpoint provides?
    ret = []
    for mw in _application.middlewares:
        cur = {}
        cur['type_name'] = mw.__class__.__name__
        cur['provides'] = mw.provides
        cur['requires'] = mw.requires
        cur['repr'] = repr(mw)
        ret.append(cur)
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


class AshesMetaPeripheral(MetaPeripheral):
    def __init__(self):
        arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self.loaded_template = arf.env.load(self.template_path)

    def render_main_page_html(self, context):
        return self.loaded_template.render(context)


class BasicPeripheral(MetaPeripheral):
    title = 'Basic Peripheral'
    group_key = 'basic'

    def get_context(self, _meta_application):
        start_time = _meta_application.resources['_meta_start_time']
        return {'abs_start_time': str(start_time),
                'rel_start_time': rel_datetime(start_time)}

    def get_general_items(self, context):
        return [('Start time', (context['rel_start_time'],
                                context['abs_start_time']))]


class RoutePeripheral(AshesMetaPeripheral):
    title = 'Routes'
    group_key = 'app'
    template_path = 'meta_route_section.html'

    def get_context(self, _application, script_root):
        return {'routes': get_route_infos(_application),
                'script_root': script_root}


class MiddlewarePeripheral(AshesMetaPeripheral):
    title = 'Application-wide Middlewares'
    group_key = 'app'
    template_path = 'meta_mw_section.html'

    def get_context(self, _application):
        return {'middlewares': get_mw_infos(_application)}


class ResourcePeripheral(AshesMetaPeripheral):
    title = 'Application Resources'
    group_key = 'app'
    template_path = 'meta_resource_section.html'

    def get_context(self, _application):
        return {'resources': get_resource_info(_application)}


class ProcessPeripheral(AshesMetaPeripheral):
    title = 'Process IDs and Settings'
    group_key = 'proc'
    template_path = 'meta_proc_section.html'

    get_context = staticmethod(get_proc_info)

    def get_general_items(self, context):
        return [('PID', context['pid'])]


class HostPeripheral(AshesMetaPeripheral):
    title = 'Host Information'
    group_key = 'host'
    template_path = 'meta_host_section.html'

    get_context = staticmethod(get_host_info)

    def get_general_items(self, context):
        ret = []
        load_avgs = context.get('load_avgs')
        if load_avgs:
            ret.append(('Load averages', repr(load_avgs)))
        return ret


class ResourceUsagePeripheral(AshesMetaPeripheral):
    title = 'Process Resource Usage'
    group_key = 'rusage'
    template_path = 'meta_rusage_section.html'

    def get_context(self):
        rusage = get_rusage_dict()
        rusage['rlimit'] = get_rlimit_dict()
        return rusage


class PythonPeripheral(AshesMetaPeripheral):
    title = 'Python Runtime'
    group_key = 'pyvm'
    template_path = 'meta_pyvm_section.html'

    get_context = staticmethod(get_pyvm_info)


class SysconfigPeripheral(MetaPeripheral):
    title = 'Python System Configuration'
    group_key = 'pyvm'

    def get_context(self):
        ret = {}
        try:
            ret['sysconfig'] = sysconfig.get_config_vars()
        except:
            pass
        try:
            ret['paths'] = sysconfig.get_paths()
        except:
            pass
        return ret


DEFAULT_PERIPHERALS = [BasicPeripheral(),
                       RoutePeripheral(),
                       MiddlewarePeripheral(),
                       ResourcePeripheral(),
                       HostPeripheral(),
                       ProcessPeripheral(),
                       ResourceUsagePeripheral(),
                       PythonPeripheral(),
                       SysconfigPeripheral()]


class MetaApplication(Application):
    def __init__(self, peripherals=None, page_title=DEFAULT_PAGE_TITLE,
                 base_peripherals=DEFAULT_PERIPHERALS):
        self.page_title = page_title
        self.peripherals = list(base_peripherals)
        self.peripherals.extend(peripherals or [])

        self._arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
        self._main_page_render = self._arf('meta_base.html')
        routes = [('/', self.get_main, self.render_main_page_html),
                  ('/clastic_assets/', StaticApplication(_ASSET_PATH)),
                  ('/json/', self.get_main, render_json)]
        for peri in self.peripherals:
            routes.extend(peri.get_extra_routes())
        resources = {'_meta_start_time': datetime.datetime.utcnow(),
                     'page_title': page_title}

        mwares = [ScriptRootMiddleware(),
                  SimpleContextProcessor('script_root')]
        super(MetaApplication, self).__init__(routes, resources, mwares)

    def get_main(self, request, _application, _route, script_root):
        full_ctx = {'page_title': self.page_title}
        kwargs = {'request': request,
                  '_route': _route,
                  '_application': _application,
                  '_meta_application': self,
                  'script_root': script_root}
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
                cur_context = context[peri.group_key]
                kwargs = {'context': cur_context}
                cur['content'] = inject(peri.render_main_page_html, kwargs)

                prev_exc = cur_context.get('exc_content')
                if prev_exc:
                    cur['exc_content'] = prev_exc
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
