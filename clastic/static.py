# -*- coding: utf-8 -*-

import os
import mimetypes
from os.path import isfile, join as pjoin
from datetime import datetime

from werkzeug.wsgi import FileWrapper
from werkzeug.wrappers import Response

from core import Application
from errors import Forbidden, NotFound

# TODO: check isdir and accessible on search_paths
# TODO: default favicon.ico StaticApplication?
# TODO: process paths

DEFAULT_MAX_AGE = 360
DEFAULT_TEXT_MIME = 'text/plain'
DEFAULT_BINARY_MIME = 'application/octet-stream'

# string.printable doesn't cut it
_PRINTABLE = ''.join([chr(x) for x in [7, 8, 9, 10, 12, 13, 27] +
                      range(32, 256)])


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
    if rel_path.startswith(os.pardir) and limit_root:
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


class StaticApplication(Application):
    def __init__(self,
                 search_paths,
                 check_paths=True,
                 cache_timeout=DEFAULT_MAX_AGE,
                 default_text_mime=DEFAULT_TEXT_MIME,
                 default_binary_mime=DEFAULT_BINARY_MIME):
        if isinstance(search_paths, basestring):
            search_paths = [search_paths]
        self.search_paths = search_paths
        self.cache_timeout = cache_timeout
        self.default_text_mime = default_text_mime
        self.default_binary_mime = default_binary_mime
        routes = [('/<path:path>', self.get_file_response)]
        super(StaticApplication, self).__init__(routes)

    def get_file_response(self, path, request):
        try:
            full_path = find_file(self.search_paths, path)
            if full_path is None:
                raise NotFound()
            file_obj = open(full_path, 'rb')
            mtime = get_file_mtime(full_path)
            fsize = os.path.getsize(full_path)
        except (ValueError, IOError, OSError):
            raise Forbidden()
        mimetype, encoding = mimetypes.guess_type(full_path)
        if not mimetype:
            peeked = peek_file(file_obj, 1024)
            is_binary = is_binary_string(peeked)
            if peeked and is_binary:
                mimetype = self.default_binary_mime
            else:
                mimetype = self.default_text_mime  # TODO: binary

        resp = Response('')
        cached_mtime = request.if_modified_since
        if self.cache_timeout:
            resp.cache_control.public = True
            if mtime == cached_mtime:
                file_obj.close()
                resp.status_code = 304
                resp.cache_control.max_age = self.cache_timeout
                return resp
        file_wrapper = request.environ.get('wsgi.file_wrapper', FileWrapper)
        resp.response = file_wrapper(file_obj)
        resp.content_type = mimetype
        resp.content_length = fsize
        resp.last_modified = mtime
        return resp


if __name__ == '__main__':
    CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    app = StaticApplication(CUR_DIR)
    app.serve()
