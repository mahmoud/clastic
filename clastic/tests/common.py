import clastic
from clastic import Middleware


def hello_world(name=None):
    if name is None:
        name = 'world'
    return clastic.Response("Hello, %s!" % name)


class RequestProvidesName(Middleware):
    provides = ('name',)

    def __init__(self, default_name=None):
        self.default_name = default_name

    def request(self, next, request):
        try:
            ret = next(request.args.get('name', self.default_name))
        except Exception as e:
            raise
        return ret
