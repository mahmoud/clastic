from __future__ import unicode_literals
import os
from nose.tools import raises, eq_, ok_

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from clastic import Application
from clastic.render.mako_templates import mako, MakoRenderFactory
from clastic.render import render_basic

from common import hello_world_ctx, complex_context

_TMPL_DIR = os.path.join(os.path.dirname(__file__), '_mako_tmpls')


def test_mako():
    mako_render = MakoRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.html'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/<name>/', hello_world_ctx, tmpl),
                       ('/beta/<name>/', complex_context, tmpl)],
                      render_factory=mako_render)

    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.status_code, 200
    yield ok_, 'clasty' in resp.data

    resp = c.get('/beta/Rajkumar/')
    yield eq_, resp.status_code, 200
    yield ok_, 'clasty' in resp.data


@raises(mako.exceptions.TopLevelLookupException)
def test_mako_missing_template():
    mako_render = MakoRenderFactory(_TMPL_DIR)
    tmpl = 'missing_template.html'
    return Application([('/', hello_world_ctx, tmpl)],
                       render_factory=mako_render)


def test_mako_broken_template():
    mako_render = MakoRenderFactory(_TMPL_DIR)
    tmpl = 'broken_template_1.html'
    app = Application([('/', hello_world_ctx, tmpl)],
                      render_factory=mako_render)
    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.status_code, 500
    yield ok_, len(resp.data) > 1024  # a longish response


def test_mako_mixed():
    mako_render = MakoRenderFactory(_TMPL_DIR)
    tmpl = 'basic_template.html'
    app = Application([('/', hello_world_ctx, tmpl),
                       ('/json/', hello_world_ctx, render_basic)],
                      render_factory=mako_render)

    c = Client(app, BaseResponse)
    resp = c.get('/')
    yield eq_, resp.status_code, 200
    yield ok_, 'clasty' in resp.data

    resp = c.get('/json/')
    yield eq_, resp.status_code, 200
