# -*- coding: utf-8 -*-

import gc
import sys
import types

from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from application import Application

# TODO: lintutils check on sys.modules


class ObjectBrowserApplication(Application):
    def __init__(self, default_obj=None):
        self.default_obj = default_obj or self  # TODO: pass through to_url

        super_init = super(ObjectBrowserApplication, self).__init__
        super_init([('/object', self.view_obj),
                    ('/object/<obj_id:int>', self.view_obj)])

    def view_obj(self, request, obj_id=None):
        if obj_id is None:
            default_path = request.path + ('/%s' % id(self.default_obj))
            return redirect(default_path)

        for obj in gc.get_objects():
            if id(obj) == obj_id:
                break
        else:
            raise ValueError("no Python object with id %s" % obj_id)

        path, _, _ = request.path.rpartition('/')
        renderer = ObjectRenderer(path_prefix=path)
        return Response(renderer.render_page(obj), mimetype="text/html")


class ObjectRenderer(object):
    def __init__(self, path_prefix=''):
        self.path_prefix = path_prefix

    def to_bytes(self, obj):
        if isinstance(obj, str):
            return obj
        if isinstance(obj, unicode):
            ret = obj.encode('utf-8', 'replace')
        else:
            ret = repr(obj)  # repr is usually unicode or bytes?
        return ret

    def to_url(self, obj):
        return self.path_prefix + '/' + str(id(obj))

    def to_link(self, obj):
        try:
            title = object.__repr__(obj)
        except:
            title = '<unreprable %s object>' % obj.__class__.__name__
        obj_bytes = self.to_bytes(obj)
        if gc.is_tracked(obj):
            return '<span title="%s">%s</span>' % (title, obj_bytes)
        return ('<a title="%s" href="%s">%s</a>'
                % (title, self.to_url(obj), obj_bytes))
