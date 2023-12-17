# -*- coding: utf-8 -*-

import sys
import itertools
from json import JSONEncoder
from collections.abc import Mapping, Sized, Iterable

from werkzeug.wrappers import Response

from .tabular import TabularRender

class ClasticJSONEncoder(JSONEncoder):
    def __init__(self, **kw):
        self.dev_mode = kw.pop('dev_mode', False)
        kw.setdefault('skipkeys', True)
        kw.setdefault('ensure_ascii', True)
        kw.setdefault('indent', 2)
        kw.setdefault('sort_keys', True)
        kw.pop('encoding', None)
        super(ClasticJSONEncoder, self).__init__(**kw)

    def default(self, obj):
        if isinstance(obj, Mapping):
            try:
                return dict(obj)
            except Exception:
                pass
        if isinstance(obj, Sized) and isinstance(obj, Iterable):
            try:
                return list(obj)
            except Exception:
                pass
        if not isinstance(obj, type):
            if callable(getattr(obj, 'to_dict', None)):
                return obj.to_dict()
            if callable(getattr(obj, 'asdict', None)):
                return obj.asdict()
            if callable(getattr(obj, 'isoformat', None)):
                return obj.isoformat()

        if self.dev_mode:
            return repr(obj)
        raise TypeError('cannot serialize to JSON: %r' % obj)


class JSONRender(object):
    def __init__(self, streaming=False, dev_mode=False, encoding='utf-8'):
        self.streaming = streaming
        self.dev_mode = dev_mode
        self.encoding = encoding
        self.json_encoder = ClasticJSONEncoder(encoding=encoding,
                                               dev_mode=self.dev_mode)

    def __call__(self, context):
        if self.streaming:
            json_iter = self.json_encoder.iterencode(context)
        else:
            json_iter = [self.json_encoder.encode(context)]
        resp = Response(json_iter, mimetype="application/json")
        resp.mimetype_params['charset'] = self.encoding
        return resp


class JSONPRender(JSONRender):
    def __init__(self, qp_name='callback', *a, **kw):
        self.qp_name = qp_name
        super(JSONPRender, self).__init__(*a, **kw)

    def __call__(self, request, context):
        cb_name = request.args.get(self.qp_name, None)
        if not cb_name:
            return super(JSONPRender, self).__call__(context)
        json_iter = self.json_encoder.iterencode(context)
        resp_iter = itertools.chain([cb_name, '('], json_iter, [');'])
        resp = Response(resp_iter, mimetype="application/javascript")
        resp.mimetype_params['charset'] = self.encoding
        return resp


class BasicRender(object):
    _default_mime = 'application/json'
    _format_mime_map = {'html': 'text/html',
                        'json': 'application/json'}

    def __init__(self, **kwargs):
        self.qp_name = kwargs.pop('qp_name', 'format')
        self.dev_mode = kwargs.pop('dev_mode', True)
        self.json_render = kwargs.pop('json_render',
                                      JSONRender(dev_mode=self.dev_mode))
        try:
            table_type = kwargs.pop('table_type')
        except KeyError:
            table_type = None
            default_tabular = TabularRender()
        else:
            default_tabular = TabularRender(table_type=table_type)

        self.tabular_render = kwargs.pop('tabular_render', default_tabular)
        if kwargs:
            raise TypeError('unexpected keyword arguments: %r' % kwargs)

    def render_response(self, context, request, _route):
        if isinstance(context, str):  # already serialized but not encoded
            context = context.encode('utf8')
        if isinstance(context, bytes):  # already serialized and encoded
            if self._guess_json(context):
                return Response(context, mimetype="application/json")
            elif b'<html' in context[:168]:
                # based on the longest DOCTYPE I found in a brief search
                return Response(context, mimetype="text/html")
            else:
                return Response(context, mimetype="text/plain")

        # not serialized yet, time to guess what the requester wants
        if not isinstance(context, Sized):
            return Response(unicode(context), mimetype="text/plain")
        return self._serialize_to_resp(context, request, _route)

    __call__ = render_response

    def _serialize_to_resp(self, context, request, _route):
        req_format = request.args.get(self.qp_name)  # explicit GET query param
        if req_format and req_format not in self._format_mime_map:
            # TODO: badrequest
            raise ValueError('format expected one of %r, not %r'
                             % (self.formats, req_format))

        resp_mime = self._format_mime_map.get(req_format)
        if not resp_mime and request.accept_mimetypes:
            resp_mime = request.accept_mimetypes.best_match(self.mimetypes)
        if resp_mime not in self._mime_format_map:
            resp_mime = self._default_mime

        if resp_mime == 'application/json':
            return self.json_render(context)
        elif resp_mime == 'text/html':
            return self.tabular_render(context, _route)
        return Response(str(context), mimetype="text/plain")

    @property
    def _mime_format_map(self):
        return dict([(v, k) for k, v in self._format_mime_map.items()])

    @property
    def formats(self):
        return self._format_mime_map.keys()

    @property
    def mimetypes(self):
        return self._format_mime_map.values()

    @staticmethod
    def _guess_json(bytestr: bytes):
        if not bytestr:
            return False
        elif bytestr[0] == b'{' and bytestr[-1] == b'}':
            return True
        elif bytestr[0] == b'[' and bytestr[-1] == b']':
            return True
        else:
            return False

    @classmethod
    def factory(cls, *a, **kw):
        def basic_render_factory(render_arg):
            # behavior doesn't change depending on render_arg
            return cls(*a, **kw)
        return basic_render_factory


render_json = JSONRender()
render_json_dev = JSONRender(dev_mode=True)
render_basic = BasicRender()
