from __future__ import unicode_literals
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

import clastic
from clastic import Application, Middleware


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


def test_blank_req_provides():
    req_provides_blank = RequestProvidesName()
    app = Application([('/', hello_world)],
                      middlewares=[req_provides_blank])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    eq_(resp.data, 'Hello, world!')
    resp = c.get('/?name=Kurt')
    eq_(resp.data, 'Hello, Kurt!')


def test_req_provides():
    req_provides = RequestProvidesName('Rajkumar')
    app = Application([('/', hello_world)],
                      middlewares=[req_provides])
    c = Client(app, BaseResponse)
    resp = c.get('/')
    eq_(resp.data, 'Hello, Rajkumar!')
    resp = c.get('/?name=Kurt')
    eq_(resp.data, 'Hello, Kurt!')

    return app

@raises(NameError)
def test_duplicate_mw():
    req_provides1 = RequestProvidesName('Rajkumar')
    req_provides2 = RequestProvidesName('Jimmy John')
    app = Application([('/', hello_world)],
                      middlewares=[req_provides1,
                                   req_provides2])
    return app
