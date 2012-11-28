# -*- encoding:utf-8 -*-
from __future__ import unicode_literals

import mako
from mako.lookup import TemplateLookup

from werkzeug.wrappers import Response

class MakoRenderFactory(object):
    def __init__(self, template_dirs, **kw):
        kw.setdefault('format_exceptions', True)
        self.lookup = TemplateLookup(template_dirs, **kw)

    def __call__(self, template_filename):
        template = self.lookup.get_template(template_filename)

        def mako_render(context):
            return Response(template.render_unicode(**context),
                            mimetype='text/html')

        return mako_render
