import os
import sys
import socket
import signal
import thread
import subprocess
from itertools import chain
from ast import literal_eval

import werkzeug.serving
from werkzeug._internal import _log
from werkzeug.serving import reloader_loop, make_server


def open_test_socket(host, port):
    fam = socket.AF_INET4
    if ':' in host:
        fam = getattr(socket, 'AF_INET6', socket.AF_INET4)
    test_socket = socket.socket(fam, socket.SOCK_STREAM)
    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_socket.bind((host, port))
    test_socket.close()


def _iter_module_files():
    unique_files = set()
    for module in sys.modules.values():
        filename = getattr(module, '__file__', None)
        if filename:
            old = None
            while not os.path.isfile(filename):
                old = filename
                filename = os.path.dirname(filename)
                if filename == old:
                    break
            else:
                if filename[-4:] in ('.pyc', '.pyo'):
                    filename = filename[:-1]
                if filename not in unique_files:
                    unique_files.add(filename)
                    yield filename


def test():
    print 'testtesttesttest'
    return


def restart_with_reloader():
    to_mon = []
    while 1:
        _log('info', ' * Clastic restarting with reloader')
        args = [sys.executable] + sys.argv
        new_environ = os.environ.copy()
        new_environ['WERKZEUG_RUN_MAIN'] = 'true'

        # a weird bug on windows. sometimes unicode strings end up in the
        # environment and subprocess.call does not like this, encode them
        # to latin1 and continue.
        if os.name == 'nt':
            for key, value in new_environ.iteritems():
                if isinstance(value, unicode):
                    new_environ[key] = value.encode('iso-8859-1')
        child_proc = subprocess.Popen(args, env=new_environ, stderr=subprocess.PIPE)
        _, stderr_data = child_proc.communicate()
        exit_code = child_proc.returncode
        if exit_code == 3:
            try:
                to_mon = literal_eval(stderr_data.splitlines()[-1])
            except:
                to_mon = []
                continue
        elif exit_code == 1 and stderr_data:
            from clastic.meta import MetaApplication
            print 'running error app'
            import inspect
            print len(inspect.stack())
            # import pdb;pdb.set_trace()
            def inner():
                make_server('localhost', 5000, MetaApplication).serve_forever()
            thread.start_new_thread(inner, ())
            try:
                reloader_loop(to_mon, 1)
            except KeyboardInterrupt:
                pass
            print 'error app returned'
            continue
        else:
            return exit_code


werkzeug.serving.restart_with_reloader = restart_with_reloader


def run_with_reloader(main_func, extra_files=None, interval=1):
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        thread.start_new_thread(main_func, ())
        try:
            reloader_loop(extra_files, interval)
        except KeyboardInterrupt:
            return
        except SystemExit:
            mon_list = list(chain(_iter_module_files(), extra_files or ()))
            sys.stderr.write(repr(mon_list))
            raise
    try:
        sys.exit(restart_with_reloader())
    except KeyboardInterrupt:
        pass


werkzeug.serving.run_with_reloader = run_with_reloader


"""
def run_simple(hostname, port, application, use_reloader=False,
               use_debugger=False, use_evalex=True, extra_files=None,
               reloader_interval=1, passthrough_errors=False,
               ssl_context=None):
    pass
"""
