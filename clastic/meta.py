# -*- coding: utf-8 -*-

import os
import sys
import socket
import platform
import datetime

from glom import glom, T, Call, Coalesce
from boltons.strutils import bytes2human
from boltons.timeutils import relative_time


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
    import getpass
except:
    getpass = None

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

try:
    unicode
except NameError:
    # py3
    unicode = str


from .application import Application, NullRoute, RESERVED_ARGS
from .sinter import inject, get_fb, get_callable_name
from .render import render_json, AshesRenderFactory
from .static import StaticApplication


from .middleware.url import ScriptRootMiddleware
from .middleware.context import SimpleContextProcessor


_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_ASSET_PATH = os.path.join(_CUR_PATH, '_clastic_assets')
META_ASSETS_APP = StaticApplication(_ASSET_PATH)

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

    ret['owner'] = glom(globals(), Coalesce(T['getpass'].getuser(),
                                            T['os'].getuid()),
                        skip_exc=Exception)

    # use 0 to get current niceness, seems to return process group's nice level
    unix_only_vals = glom(os, {'ppid': T.getppid(),
                               'pgid': T.getpgrp(),
                               'niceness': T.nice(0)},
                          skip_exc=AttributeError)
    ret.update(unix_only_vals)

    ret['rusage'] = get_rusage_dict()
    ret['rlimit'] = get_rlimit_dict()
    return ret


# TODO: byte order, path, prefix
def get_host_info():
    ret = {}
    now = datetime.datetime.utcnow()

    ret['hostname'] = socket.gethostname()
    ret['hostfqdn'] = socket.getfqdn()
    ret['uname'] = platform.uname()
    ret['cpu_count'] = CPU_COUNT
    ret['platform'] = platform.platform()
    ret['platform_terse'] = platform.platform(terse=True)

    ret['load_avgs'] = glom(os, T.getloadavg(), skip_exc=AttributeError)

    ret['utc_time'] = str(now)
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

    ret['active_thread_count'] = glom(sys, (T._current_frames(), len), skip_exc=Exception)
    ret['recursion_limit'] = sys.getrecursionlimit()

    ret['gc'] = glom(None, Call(get_gc_info), skip_exc=Exception)  # effectively try/except:pass

    get_interval = getattr(sys, 'getswitchinterval', sys.getcheckinterval)
    ret['check_interval'] = get_interval()
    return ret


def get_gc_info():
    import gc
    ret = {}
    ret['is_enabled'] = gc.isenabled()
    ret['thresholds'] = gc.get_threshold()

    ret['counts'] = glom(gc, T.get_count(), skip_exc=Exception)
    ret['obj_count'] = glom(gc, (T.get_objects(), len), skip_exc=Exception)

    return ret


def get_resource_info(_application):
    ret = []
    for key, val in _application.resources.items():
        if 'secret' in key:
            trunc_val = '[REDACTED]'
        else:
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
        ret['module_name'], ret['name'] = get_callable_name(route.endpoint)
    except AttributeError:
        try:
            ret['name'] = repr(route.endpoint)
        except:
            ret['name'] = object.__repr__(route.endpoint)
    return ret


def get_render_info(route):
    ret = {'type': None}
    render_arg = route.render_arg
    if route.render_factory and not callable(render_arg):
        ret['type'] = route.render_factory.__class__.__name__
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
    fb = get_fb(route.endpoint)
    r_args = fb.args
    r_defaults = fb.get_defaults_dict()
    arg_srcs = []
    for arg in r_args:
        arg_src = {'name': arg}
        source = None
        if arg in RESERVED_ARGS:
            source = 'builtin'
        elif arg in route.path_args:
            source = 'url'
        elif arg in route.resources:
            source = 'resources'
        else:
            for mw in route.middlewares:
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
                'rel_start_time': relative_time(start_time)}

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
        ret['sysconfig'] = glom(sysconfig, T.get_config_vars(), skip_exc=Exception)
        ret['paths'] = glom(sysconfig, T.get_paths(), skip_exc=Exception)
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
                  ('/clastic_assets/', META_ASSETS_APP),
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
        if isinstance(key, (bytes, unicode)):
            cur['key'] = key
        else:
            try:
                cur['key'] = unicode(key[0])
                cur['key_detail'] = unicode(key[1])
            except:
                cur['key'] = unicode(key)
        if isinstance(value, (bytes, unicode)):
            cur['value'] = value
        else:
            try:
                cur['value'] = unicode(value[0])
                cur['value_detail'] = unicode(value[1])
            except:
                cur['value'] = str(value)
        ret.append(cur)
    return ret
