# -*- coding: utf-8 -*-

from gzip import GzipFile
from StringIO import StringIO

from .core import Middleware


def compress(data, level=6):
    out = StringIO()
    f = GzipFile(fileobj=out, mode='wb', compresslevel=level)
    f.write(data)
    f.close()
    return out.getvalue()


class GzipMiddleware(Middleware):
    def __init__(self, compress_level=6):
        self.compress_level = compress_level

    def request(self, next, request):
        resp = next()
        # TODO: shortcut redirects/304s/responses without content?
        resp.vary.add('Accept-Encoding')
        if resp.content_encoding or not request.accept_encodings['gzip']:
            return resp

        if 'msie' in request.user_agent.browser:
            if not (resp.content_type.startswith('text/') or
                    'javascript' in resp.content_type):
                return resp

        if resp.is_streamed:
            return resp  # TODO
        else:
            comp_content = compress(resp.data, self.compress_level)
            if len(comp_content) >= len(resp.data):
                return resp
            resp.response = [comp_content]
            resp.content_length = len(comp_content)

        resp.content_encoding = 'gzip'
        # TODO: regenerate etag?
        return resp
