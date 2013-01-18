# -*- encoding:utf-8 -*-
from __future__ import unicode_literals

import os
from os.path import splitext, basename, join as pjoin
import sys
import traceback

from werkzeug.wrappers import Response

from dust import DustEnv
"""
the dust library used here is intended to be one compatible with
https://github.com/mahmoud/dust.py , not the Google Code version,
which is severely broked.
"""

"""
TODO
 * directory-namespacing of templates
 * support autoreloading of changed templates for development ease
 * support recursive=False
"""


_EXT_MAP = {'.html': 'text/html',
            '.htm': 'text/html',
            '.txt': 'text/plain',
            '.xml': 'application/xml'}


def match_extension(path, ext=''):
    if ext:
        ext = '.' + ext.lstrip('.')
    return path.endswith(ext)


def get_template_name(template_path):
    return splitext(basename(template_path))[0]


def walk_template_path(template_path, exts=None):
    if not exts:
        exts = _EXT_MAP.keys()
    matches = []
    for root, _, filenames in os.walk(template_path):
        for fn in filenames:
            for ext in exts:
                if match_extension(fn, ext):
                    matches.append(pjoin(root, fn))
    return matches


class DustRenderFactory(object):
    def __init__(self,
                 template_dirs,
                 recursive=True,
                 mime_map=None,
                 default_mime=None, **kw):
        self.default_mime = default_mime or 'text/html'
        self.mime_map = mime_map or dict(_EXT_MAP)
        self.mime_map['.dust'] = self.default_mime
        if isinstance(template_dirs, basestring):
            template_dirs = [template_dirs]
        self.template_dirs = template_dirs
        self.filename_map = {}
        self.dust_env = DustEnv()
        self._load_templates()

    def _load_templates(self):
        exts = self.mime_map.keys()
        for td in self.template_dirs:
            t_paths = walk_template_path(td, exts=exts)
            for path in t_paths:
                filename = basename(path)
                name = get_template_name(path)
                try:
                    self.dust_env.load(path, name)
                except Exception as e:
                    sys.stderr.write('failed to load %s (%s)\n' % name, path)
                    #import pdb;pdb.post_mortem()
                else:
                    self.filename_map[filename] = name

    def __call__(self, filename_or_name):
        # trigger error if not found
        filename = self.filename_map.get(filename_or_name, filename_or_name)
        template_name = get_template_name(filename_or_name)
        if not self.dust_env.templates.get(template_name):
            raise KeyError('no template found with name "%s"' % template_name)
        try:
            success_mimetype = self.mime_map[splitext(filename)[1]]
        except KeyError:
            success_mimetype = self.default_mime

        def dust_render(context):
            mimetype = success_mimetype  # oh nonlocals, you
            status = 200
            try:
                content = self.dust_env.render(template_name, context)
            except:
                status = 500
                mimetype = 'text/plain'
                content = traceback.format_exc()
            return Response(content, status=status, mimetype=mimetype)

        return dust_render
