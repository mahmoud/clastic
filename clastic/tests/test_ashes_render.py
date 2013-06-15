from __future__ import unicode_literals
import os
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.render import ashes
from clastic.render import AshesRenderFactory, render_basic

from common import hello_world_ctx, complex_context

_TMPL_DIR = os.path.join(os.path.dirname(__file__), '_ashes_tmpls')


def test_ashes():
    ashes_render = AshesRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.html'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/<name>/', hello_world_ctx, tmpl),
                       ('/beta/<name>/', complex_context, tmpl)],
                      render_factory=ashes_render)

    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.status_code, 200
    yield ok_, 'world' in resp.data

    resp = c.get('/beta/Rajkumar/')
    yield eq_, resp.status_code, 200
    yield ok_, 'Rajkumar' in resp.data


@raises(ashes.TemplateNotFound)
def test_ashes_missing_template():
    ashes_render = AshesRenderFactory(_TMPL_DIR)
    tmpl = 'missing_template.html'
    return Application([('/', hello_world_ctx, tmpl)],
                       render_factory=ashes_render)


def test_ashes_mixed():
    ashes_render = AshesRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.html'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/json/', hello_world_ctx, render_basic)],
                      render_factory=ashes_render)

    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.status_code, 200
    yield ok_, 'Salam' in resp.data

    resp = c.get('/json/')
    yield eq_, resp.status_code, 200
