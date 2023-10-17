# -*- coding: utf-8 -*-

import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from chameleon import PageTemplateLoader

from werkzeug.wrappers import Response


_EXT_MAP = {'.html': 'text/html',
            '.htm': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.js': 'application/javascript',
            '.txt': 'text/plain',
            '.xml': 'application/xml'}


def error_template(format="text"):
    import traceback
    out = StringIO()
    if format == "html":
        out.write("""<!DOCTYPE html>\n<body>\n<pre>\n""")
    traceback.print_exc(file=out)
    if format == "html":
        out.write("""</pre>\n</body>\n</html>\n""")
    return out.getvalue()


class ChameleonRenderFactory(object):
    def __init__(self, template_dirs, default_mime=None, **kw):
        # we'll handle the exception formatting, thanks.
        self.format_exceptions = kw.pop('format_exceptions', True)

        self.lookup = PageTemplateLoader(template_dirs, **kw)
        self.default_mime = default_mime or 'text/html'

    def __call__(self, template_filename):
        # trigger error if not found
        tmp_template = self.lookup[template_filename]
        for ext, mt in _EXT_MAP.items():
            if template_filename.endswith(ext):
                mimetype = mt
                break
        else:
            mimetype = self.default_mime

        def chameleon_render(context):
            status = 200
            template = self.lookup[template_filename]
            try:
                content = template(**context)
            except:
                if not self.format_exceptions:
                    raise
                status = 500
                if mimetype == 'text/html':
                    content = error_template(format="html")
                else:
                    # TODO: add handling for other mimetypes?
                    content = error_template()
            return Response(content, status=status, mimetype=mimetype)

        return chameleon_render
