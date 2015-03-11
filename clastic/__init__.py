# -*- coding: utf-8 -*-

"""
    clastic
    ~~~~~~~

    A functional Python web framework that streamlines explicit
    development practices while eliminating global state.

    :copyright: (c) 2012 by Mahmoud Hashemi
    :license: BSD, see LICENSE for more details.

"""
try:
    import werkzeug
except ImportError:
    missing_dep_msg = 'clastic depends on werkzeug. check that you have the right virtualenv activated or run `easy_install werkzeug` or `pip install werkzeug`.'
    raise ImportError(missing_dep_msg)

import server

from application import Application, SubApplication
from route import Route, GET, POST, PUT, DELETE, RESERVED_ARGS

from middleware import Middleware, GetParamMiddleware
from render import render_json, render_json_dev, render_basic
from meta import MetaApplication
from static import StaticApplication, StaticFileRoute
from errors import HTTPException

from werkzeug.wrappers import BaseRequest, Request, BaseResponse, Response
from werkzeug.utils import redirect, append_slash_redirect


# TODO: deprecate
from render import json_response, default_response
