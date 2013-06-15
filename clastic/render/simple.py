from json import JSONEncoder
from collections import Mapping, Sized, Iterable

from werkzeug.wrappers import Response


class ClasticJSONEncoder(JSONEncoder):
    def __init__(self, **kw):
        self.dev_mode = kw.pop('dev_mode', False)
        kw.setdefault('skipkeys', True)
        kw.setdefault('ensure_ascii', False)
        kw.setdefault('indent', 2)
        kw.setdefault('sort_keys', True)
        super(ClasticJSONEncoder, self).__init__(**kw)

    def default(self, obj):
        if isinstance(obj, Mapping):
            try:
                return dict(obj)
            except:
                pass
        if isinstance(obj, Sized) and isinstance(obj, Iterable):
            return list(obj)
        if callable(getattr(obj, 'to_dict', None)):
            return obj.to_dict()

        if self.dev_mode:
            return repr(obj)  # TODO: blargh
            if isinstance(obj, type) or callable(obj):
                return unicode(repr(obj))
            try:
                return dict([(k, v) for k, v in obj.__dict__.items()
                             if not k.startswith('__')])
            except AttributeError:
                return unicode(repr(obj))
        else:
            raise TypeError('cannot serialize to JSON: %r' % obj)


class JSONRender(object):
    def __init__(self, dev_mode=False, encoding='utf-8'):
        self.dev_mode = dev_mode
        self.encoding = encoding
        self.json_encoder = ClasticJSONEncoder(encoding=encoding,
                                               dev_mode=self.dev_mode)

    def __call__(self, context):
        json_iter = self.json_encoder.iterencode(context)
        resp = Response(json_iter, mimetype="application/json")
        resp.mimetype_params['charset'] = self.encoding
        return resp


class BasicRender(object):
    def __init__(self, dev_mode=True):
        self.json_render = JSONRender(dev_mode=dev_mode)

    def __call__(self, context):
        if isinstance(context, basestring):
            if '<html' in context[:98]:
                return Response(context, mimetype="text/html")
            else:
                return Response(context, mimetype="text/plain")
        if isinstance(context, Sized):
            try:
                return self.json_render(context)
            except:
                pass
        return Response(unicode(context), mimetype="text/plain")


render_json = JSONRender()
render_json_dev = JSONRender(dev_mode=True)
render_basic = BasicRender()


#TODO: deprecate


DefaultRender = BasicRender
json_response = render_json
dev_json_response = render_json_dev
default_response = render_basic
