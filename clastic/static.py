# -*- coding: utf-8 -*-

import os
import mimetypes
from os.path import isfile, join as pjoin
from datetime import datetime

from werkzeug.wsgi import FileWrapper
from werkzeug.wrappers import Response
from werkzeug.exceptions import Forbidden, NotFound

from core import Application

# TODO: caching
# TODO: check isdir and accessable on static_roots

default_mimetype = 'text/plain'  # TODO


def get_file_response(static_roots, path, file_wrapper=None):
    if file_wrapper is None:
        file_wrapper = FileWrapper
    rel_path = os.path.normpath(path)
    if rel_path.startswith(os.pardir):
        raise Forbidden('attempted to access beyond root hosted directory.')
    for sr in static_roots:
        full_path = pjoin(sr, rel_path)
        if not isfile(full_path):
            continue
        mtime = datetime.utcfromtimestamp(os.path.getmtime(full_path))
        file_obj = open(full_path, 'rb')
        fsize = os.path.getsize(full_path)
        mimetype, encoding = mimetypes.guess_type(full_path)
        if not mimetype:
            # TODO: configurable
            # TODO: check binary
            mimetype = default_mimetype
        break
    else:
        raise NotFound()

    resp = Response(FileWrapper(file_obj))
    resp.content_type = mimetype
    resp.content_length = fsize
    resp.last_modified = mtime
    return resp


def create_app(static_roots):
    if isinstance(static_roots, basestring):
        static_roots = [static_roots]
    resources = {'static_roots': static_roots}
    routes = [('/<path:path>', get_file_response)]
    app = Application(routes, resources)
    return app


if __name__ == '__main__':
    CUR_DIR = os.path.dirname(os.path.abspath(__file__))
    app = create_app(CUR_DIR)
    app.serve()
