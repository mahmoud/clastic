# -*- coding: utf-8 -*-

from werkzeug.wrappers import Response

import ashes

try:
    unicode, bytes = unicode, str
except NameError:
    # py3
    unicode = str

AshesEnv = ashes.AshesEnv


_EXT_MAP = {'.dust': None,  # None means default to default_mime
            '.ash': None,
            '.ashes': None,
            '.html': 'text/html',
            '.htm': 'text/html',
            '.txt': 'text/plain',
            '.xml': 'application/xml'}


__all__ = ['AshesRenderFactory']

# TODO: how to construct non-200 status code render functions?


class AshesRenderFactory(object):
    def __init__(self, template_paths=None, default_mime=None, **kw):
        if isinstance(template_paths, (unicode, bytes)):
            template_paths = [template_paths]

        load_all = kw.pop('load_all', False)
        env = kw.pop('env', None)
        if env is None:
            if not kw.get('exts'):
                kw['exts'] = _EXT_MAP.keys()
            env = AshesEnv(template_paths, **kw)
        self.env = env
        if load_all:
            self.env.load_all()
        self.default_mime = default_mime or 'text/html'

    def register(self, *a, **kw):
        return self.env.register(*a, **kw)

    def register_source(self, *a, **kw):
        return self.env.register_source(*a, **kw)

    def __call__(self, template_path):
        self.env.load(template_path)  # trigger error if not found

        for ext, mt in _EXT_MAP.items():
            if template_path.endswith(ext):
                mimetype = mt or self.default_mime
                break
        else:
            mimetype = self.default_mime

        return self._make_render_func(template_path, mimetype)

    def _make_render_func(self, template_path, mimetype=None):
        mimetype = mimetype or self.default_mime

        def ashes_render(context):
            status = 200
            template = self.env.load(template_path)
            content = template.render(context)  # TODO: pretty errors?
            return Response(content, status=status, mimetype=mimetype)

        return ashes_render
