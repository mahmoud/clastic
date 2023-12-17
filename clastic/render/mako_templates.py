# -*- coding: utf-8 -*-

import mako
from mako import exceptions
from mako.lookup import TemplateLookup

from werkzeug.wrappers import Response


_EXT_MAP = {'.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.js': 'application/javascript',
            '.txt': 'text/plain',
            '.xml': 'application/xml'}


class MakoRenderFactory(object):
    def __init__(self, template_dirs, default_mime=None, **kw):
        # we'll handle the exception formatting, thanks.
        self.format_exceptions = kw.pop('format_exceptions', True)

        self.lookup = TemplateLookup(template_dirs, **kw)
        self.default_mime = default_mime or 'text/html'

    def __call__(self, template_filename):
        # trigger error if not found
        tmp_template = self.lookup.get_template(template_filename)
        for ext, mt in _EXT_MAP.items():
            if template_filename.endswith(ext):
                mimetype = mt
                break
        else:
            mimetype = self.default_mime

        def mako_render(context):
            status = 200
            template = self.lookup.get_template(template_filename)
            try:
                content = template.render_unicode(**context)
            except:
                if not self.format_exceptions:
                    raise
                status = 500
                if mimetype == 'text/html':
                    content = exceptions.html_error_template().render()
                else:
                    # TODO: add handling for other mimetypes?
                    content = exceptions.text_error_template().render()
            return Response(content, status=status, mimetype=mimetype)

        return mako_render
