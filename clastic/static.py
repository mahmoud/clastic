# -*- coding: utf-8 -*-

import os
import mimetypes
from os.path import isfile, join as pjoin
from datetime import datetime

from werkzeug.wsgi import FileWrapper
from werkzeug.wrappers import Response
from werkzeug.exceptions import Forbidden, NotFound

from core import Application
from middleware import Middleware

# TODO: caching
# TODO: check isdir and accessable on search_paths
# TODO: default favicon route?

default_mimetype = 'text/plain'  # TODO
DEFAULT_MAX_AGE = 360


class StaticCachingMiddleware(Middleware):
    def __init__(self, max_age=DEFAULT_MAX_AGE):
        self.max_age = max_age

    def endpoint(self, next, request, search_paths, path=None):
        if path is None:
            return next()
        try:
            full_path = find_file(search_paths, path)
            if full_path is None:
                raise NotFound()
            unix_mtime = int(os.path.getmtime(full_path))
        except (ValueError, IOError):
            raise Forbidden()
        mtime = datetime.utcfromtimestamp(unix_mtime)
        cached_mtime = request.if_modified_since
        if mtime == cached_mtime:
            resp = Response('', 304)
            resp.cache_control.max_age = 360
        else:
            resp = next()
        resp.cache_control.public = True
        return resp


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


def get_file_response(path, search_paths, file_wrapper=None):
    if file_wrapper is None:
        file_wrapper = FileWrapper
    try:
        full_path = find_file(search_paths, path)
        if full_path is None:
            raise NotFound()
        file_obj = open(full_path, 'rb')
    except (ValueError, IOError):
        raise Forbidden()
    mtime = datetime.utcfromtimestamp(os.path.getmtime(full_path))
    fsize = os.path.getsize(full_path)
    mimetype, encoding = mimetypes.guess_type(full_path)
    if not mimetype:
        # TODO: configurable
        # TODO: check binary
        mimetype = default_mimetype

    resp = Response(FileWrapper(file_obj))
    resp.content_type = mimetype
    resp.content_length = fsize
    resp.last_modified = mtime
    return resp


def create_app(search_paths):
    if isinstance(search_paths, basestring):
        search_paths = [search_paths]
    resources = {'search_paths': search_paths}
    routes = [('/<path:path>', get_file_response)]
    cmw = StaticCachingMiddleware()
    app = Application(routes, resources, middlewares=[cmw])
    return app


if __name__ == '__main__':
    CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    app = create_app(CUR_DIR)
    app.serve()
