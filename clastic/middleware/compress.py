# -*- coding: utf-8 -*-

from gzip import GzipFile

from boltons.strutils import gzip_bytes

from .core import Middleware


class GzipMiddleware(Middleware):
    def __init__(self, compress_level=6):
        self.compress_level = compress_level

    def request(self, next, request):
        resp = next()
        # TODO: shortcut redirects/304s/responses without content?
        resp.vary.add('Accept-Encoding')
        if resp.content_encoding or not request.accept_encodings['gzip']:
            return resp

        # https://connect.microsoft.com/IE/feedback/details/1795907/content-encoding-gzip-in-response-header-is-missing-on-ie11
        if 'msie' in (request.user_agent.browser or ''):
            if not (resp.content_type.startswith('text/') or
                    'javascript' in resp.content_type):
                return resp

        if resp.is_streamed:
            return resp  # TODO

        comp_content = gzip_bytes(resp.data, self.compress_level)
        if len(comp_content) >= len(resp.data):
            return resp
        resp.response = [comp_content]
        resp.content_length = len(comp_content)
        resp.content_encoding = 'gzip'
        # TODO: regenerate etag?
        return resp
