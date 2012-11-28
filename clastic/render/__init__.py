from json import dumps, JSONEncoder
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
            if isinstance(obj, type) or callable(obj):
                return unicode(obj)
            try:
                return dict([(k, v) for k, v in obj.__dict__.items()
                             if not k.startswith('__')])
            except AttributeError:
                return unicode(obj)
        else:
            raise TypeError('cannot serialize to JSON: %r' % obj)


class JSONRender(object):
    def __init__(self, dev_mode=False):
        self.dev_mode = dev_mode
        self.json_encoder = ClasticJSONEncoder(dev_mode=self.dev_mode)


    def __call__(self, context):
        ret = self.json_encoder.encode(context)
        return Response(unicode(ret), mimetype="application/json")
