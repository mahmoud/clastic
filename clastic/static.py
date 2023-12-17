# -*- coding: utf-8 -*-

import os
import sys
import mimetypes
from os.path import isfile, join as pjoin
from datetime import datetime

from werkzeug.wsgi import FileWrapper
from werkzeug.wrappers import Response

from .route import Route
from .application import Application
from .errors import Forbidden, NotFound

# TODO: check isdir and accessible on search_paths
# TODO: default favicon.ico StaticApplication?
# TODO: process paths

DEFAULT_MAX_AGE = 360
DEFAULT_TEXT_MIME = 'text/plain'
DEFAULT_BINARY_MIME = 'application/octet-stream'

# string.printable doesn't cut it
_PRINTABLE = b''.join([chr(x).encode('latin-1')
                       for x in [7, 8, 9, 10, 12, 13, 27] +
                       list(range(32, 256))])

IS_WINDOWS = sys.platform == 'win32'


def is_binary_string(byte_string, sample_size=4096):
    if len(byte_string) > sample_size:
        byte_string = byte_string[:sample_size]
    bin_chars = byte_string.translate(None, _PRINTABLE)
    return bool(bin_chars)


def peek_file(file_obj, size=-1):
    if not callable(getattr(file_obj, 'seek', None)):
        raise TypeError('expected seekable file object, not %r' % (file_obj,))
    cur_pos = file_obj.tell()
    peek_data = file_obj.read(size)
    file_obj.seek(cur_pos)
    return peek_data


def find_file(search_paths, path, limit_root=True):
    rel_path = os.path.normpath(path)
    if limit_root:
        if rel_path.startswith('/'):
            raise ValueError('expected relative path, not %r' % path)
        if IS_WINDOWS and ':' in path:
            raise ValueError('unexpected colon in path: %r' % path)
        if rel_path.startswith(os.pardir):
            raise ValueError('attempted to access beyond root directory')
    for sr in search_paths:
        full_path = pjoin(sr, rel_path)
        if isfile(full_path):
            return full_path
    else:
        return None


def get_file_mtime(path, rounding=0):
    unix_mtime = round(os.path.getmtime(path), rounding)
    return datetime.utcfromtimestamp(unix_mtime)


def build_file_response(path,
                        cache_timeout=None,
                        cached_modify_time=None,
                        mimetype=None,
                        default_text_mime=DEFAULT_TEXT_MIME,
                        default_binary_mime=DEFAULT_BINARY_MIME,
                        file_wrapper=FileWrapper,
                        response_type=Response):
    resp = response_type('')
    if cache_timeout and cached_modify_time:
        try:
            mtime = get_file_mtime(path)
        except (ValueError, IOError, OSError):  # TODO: winnow this down
            raise Forbidden(is_breaking=False)
        resp.cache_control.public = True
        if mtime <= cached_modify_time:
            resp.status_code = 304
            resp.cache_control.max_age = cache_timeout
            return resp

    if not isfile(path):
        raise NotFound(is_breaking=False)
    try:
        file_obj = open(path, 'rb')
        mtime = get_file_mtime(path)
        fsize = os.path.getsize(path)
    except (ValueError, IOError, OSError):
        raise Forbidden(is_breaking=False)
    if not mimetype:
        mimetype, encoding = mimetypes.guess_type(path)
    if not mimetype:
        peeked = peek_file(file_obj, 1024)
        is_binary = is_binary_string(peeked)
        if peeked and is_binary:
            mimetype = default_binary_mime
        else:
            mimetype = default_text_mime
    resp.response = file_wrapper(file_obj)
    resp.content_type = mimetype
    resp.content_length = fsize
    resp.last_modified = mtime
    resp.cache_control.max_age = cache_timeout
    return resp


class StaticFileRoute(Route):
    def __init__(self, pattern, file_path, check_file=True,
                 cache_timeout=DEFAULT_MAX_AGE, mimetype=None):
        super(StaticFileRoute, self).__init__(pattern, self.get_file_response)
        self.file_path = file_path
        if check_file:
            # checking the file is readable, etc.
            open(file_path).close()
            get_file_mtime(file_path)
        self.cache_timeout = cache_timeout
        self.mimetype = mimetype

    def get_file_response(self, request):
        bfr = build_file_response
        resp = bfr(self.file_path,
                   cache_timeout=self.cache_timeout,
                   cached_modify_time=request.if_modified_since,
                   mimetype=self.mimetype,
                   file_wrapper=request.environ.get('wsgi.file_wrapper',
                                                    FileWrapper))
        return resp


class StaticApplication(Application):
    def __init__(self,
                 search_paths,
                 check_paths=True,
                 cache_timeout=DEFAULT_MAX_AGE,
                 default_text_mime=DEFAULT_TEXT_MIME,
                 default_binary_mime=DEFAULT_BINARY_MIME):
        if isinstance(search_paths, (str, bytes)):
            search_paths = [search_paths]
        self.search_paths = search_paths
        self.cache_timeout = cache_timeout
        self.default_text_mime = default_text_mime
        self.default_binary_mime = default_binary_mime
        routes = [('/<path*>', self.get_file_response)]
        super(StaticApplication, self).__init__(routes)

    def get_file_response(self, path, request):
        try:
            if not isinstance(path, (str, bytes)):
                path = '/'.join(path)
            full_path = find_file(self.search_paths, path)
            if full_path is None:
                raise NotFound(is_breaking=False)
        except (ValueError, IOError, OSError):
            raise Forbidden(is_breaking=False)
        bfr = build_file_response
        resp = bfr(full_path,
                   cache_timeout=self.cache_timeout,
                   cached_modify_time=request.if_modified_since,
                   mimetype=None,
                   default_text_mime=self.default_text_mime,
                   default_binary_mime=self.default_binary_mime,
                   file_wrapper=request.environ.get('wsgi.file_wrapper',
                                                    FileWrapper))
        return resp


if __name__ == '__main__':
    CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    app = StaticApplication(CUR_DIR)
    app.serve()
