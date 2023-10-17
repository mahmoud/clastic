# -*- coding: utf-8 -*-

from collections import deque
import os
import sys
import socket
import signal
import subprocess
from itertools import chain
from ast import literal_eval

try:
    import thread
except ImportError:
    import _thread as thread  # py3

from ._werkzeug_serving import reloader_loop, make_server


_MON_PREFIX = '__clastic_mon_files:'
_STDERR_BUFF_SIZE = 1024


def open_test_socket(host, port, raise_exc=True):
    fam = socket.AF_INET
    if ':' in host:
        fam = getattr(socket, 'AF_INET6', socket.AF_INET)
    try:
        test_socket = socket.socket(fam, socket.SOCK_STREAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_socket.bind((host, port))
        test_socket.close()
        return True
    except socket.error:
        if raise_exc:
            raise
        return False


def enable_tty_echo(tty=None):
    """
    Re-enables proper console behavior, primarily for when a reload is
    triggered at a PDB prompt.

    TODO: context manager for ignoring signals
    """
    if tty is None:
        tty = sys.stdin
    if not tty.isatty():
        return
    try:
        import termios
    except ImportError:
        return

    attr_list = termios.tcgetattr(tty)
    attr_list[3] |= termios.ECHO
    try:
        orig_handler = signal.getsignal(signal.SIGTTOU)
    except AttributeError:
        termios.tcsetattr(tty, termios.TCSANOW, attr_list)
    else:
        try:
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)
            termios.tcsetattr(tty, termios.TCSANOW, attr_list)
        finally:
            signal.signal(signal.SIGTTOU, orig_handler)
    return


def iter_monitor_files():
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


def restart_with_reloader(error_func=None):
    to_mon = []
    while 1:
        print(' * Clastic restarting with reloader')
        args = [sys.executable]
        path, basename = os.path.split(sys.argv[0])
        if basename == '__main__.py':
            pkg_name = os.path.basename(path)
            args.extend(['-m', pkg_name] + sys.argv[1:])
        else:
            args.extend(sys.argv)
        new_environ = os.environ.copy()
        new_environ['WERKZEUG_RUN_MAIN'] = 'true'
        if os.name == 'nt':
            for key, value in new_environ.iteritems():
                if isinstance(value, unicode):
                    new_environ[key] = value.encode('iso-8859-1')
        child_proc = subprocess.Popen(args,
                                      env=new_environ,
                                      stderr=subprocess.PIPE)
        stderr_buff = deque(maxlen=_STDERR_BUFF_SIZE)

        def consume_lines():
            for line in iter(child_proc.stderr.readline, ''):
                if not line:
                    break
                line_text = line.decode('utf8')
                if line_text.startswith(_MON_PREFIX):
                    to_mon[:] = literal_eval(line_text[len(_MON_PREFIX):])
                else:
                    sys.stderr.write(line_text)
                    stderr_buff.append(line_text)

        while child_proc.poll() is None:
            consume_lines()
        consume_lines()

        exit_code = child_proc.returncode
        if exit_code == 3:
            continue
        elif error_func and exit_code == 1 and stderr_buff:
            enable_tty_echo()
            tb_str = ''.join(stderr_buff)
            err_server = error_func(tb_str, to_mon)
            try:
                reloader_loop(to_mon, 1)
            except KeyboardInterrupt:
                return 0
            except SystemExit as se:
                if se.code == 3:
                    continue
                return se.code
            finally:
                err_server.shutdown()
                err_server.server_close()
            return 0
        else:
            return exit_code


def run_with_reloader(main_func, extra_files=None, interval=1,
                      error_func=None):
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    enable_tty_echo()
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        thread.start_new_thread(main_func, ())
        try:
            reloader_loop(extra_files, interval)
        except KeyboardInterrupt:
            return
        except SystemExit:
            mon_list = list(chain(iter_monitor_files(), extra_files or ()))
            sys.stderr.write('%s%r\n' % (_MON_PREFIX, mon_list))
            raise

    try:
        sys.exit(restart_with_reloader(error_func=error_func))
    except KeyboardInterrupt:
        pass


def run_simple(hostname, port, application, use_reloader=False,
               use_debugger=False, use_evalex=True, extra_files=None,
               reloader_interval=1, passthrough_errors=False, processes=None,
               threaded=False, ssl_context=None):
    if use_debugger:
        from werkzeug.debug import DebuggedApplication
        application = DebuggedApplication(application, use_evalex)

    processes = 1 if processes is None else int(processes)

    def serve_forever():
        make_server(hostname, port, application, processes=processes,
                    threaded=threaded, passthrough_errors=passthrough_errors,
                    ssl_context=ssl_context).serve_forever()

    def serve_error_app(tb_str, monitored_files):
        from clastic import flaw
        err_app = flaw.create_app(tb_str, monitored_files)
        err_server = make_server(hostname, port, err_app)
        thread.start_new_thread(err_server.serve_forever, ())
        return err_server

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        display_hostname = hostname != '*' and hostname or 'localhost'
        if ':' in display_hostname:
            display_hostname = '[%s]' % display_hostname
        print(' * Running on %s://%s:%d/' % (ssl_context is None and 'http' or 'https', display_hostname, port))

    if use_reloader:
        open_test_socket(hostname, port)
        run_with_reloader(serve_forever, extra_files, reloader_interval,
                          error_func=serve_error_app)
    else:
        serve_forever()
