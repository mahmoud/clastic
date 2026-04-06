# -*- coding: utf-8 -*-

import os
import socket
from io import StringIO

import pytest

from clastic.server import open_test_socket, iter_monitor_files, enable_tty_echo


# -- open_test_socket --

def test_open_test_socket_success():
    assert open_test_socket('127.0.0.1', 0) is True


def test_open_test_socket_occupied_raises():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        with pytest.raises(OSError):
            open_test_socket('127.0.0.1', port, raise_exc=True)
    finally:
        sock.close()


def test_open_test_socket_occupied_returns_false():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        result = open_test_socket('127.0.0.1', port, raise_exc=False)
        assert result is False
    finally:
        sock.close()


def _ipv6_available():
    """Check whether IPv6 loopback is usable on this host."""
    if not hasattr(socket, 'AF_INET6'):
        return False
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.bind(('::1', 0))
        s.close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _ipv6_available(), reason='IPv6 loopback not available')
def test_open_test_socket_ipv6():
    assert open_test_socket('::1', 0) is True


def test_open_test_socket_specific_port():
    # Discover a free port, release it, then verify open_test_socket can bind it.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
    probe.close()
    assert open_test_socket('127.0.0.1', port) is True


# -- iter_monitor_files --

def test_iter_monitor_files_returns_existing_files():
    files = list(iter_monitor_files())
    assert files, 'expected at least one monitored file'
    for f in files:
        assert os.path.isfile(f), f'yielded non-file path: {f}'


def test_iter_monitor_files_includes_this_module():
    # clastic.server is imported, so its __file__ (or the .py source) must appear.
    import clastic.server as srv
    expected = os.path.abspath(srv.__file__)
    if expected.endswith(('.pyc', '.pyo')):
        expected = expected[:-1]
    files = list(iter_monitor_files())
    abs_files = [os.path.abspath(f) for f in files]
    assert expected in abs_files


def test_iter_monitor_files_no_duplicates():
    files = list(iter_monitor_files())
    assert len(files) == len(set(files))


# -- enable_tty_echo --

def test_enable_tty_echo_non_tty():
    # StringIO.isatty() returns False, so enable_tty_echo should bail early.
    result = enable_tty_echo(tty=StringIO())
    assert result is None


def test_enable_tty_echo_default_stdin_non_tty():
    # In CI / test runners, stdin is not a tty — should return None without error.
    result = enable_tty_echo()
    assert result is None
