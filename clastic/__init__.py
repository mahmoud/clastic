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
    missing_dep_msg = 'clastic depends on werkzeug. check that you have the right virtualenv activated or run `pip install werkzeug`.'
    raise ImportError(missing_dep_msg)

from . import server

from .application import Application, SubApplication, RerouteWSGI
from .route import Route, GET, POST, PUT, DELETE, RESERVED_ARGS, S_REDIRECT, S_REWRITE, S_STRICT

from .middleware import Middleware, GetParamMiddleware
from .render import render_json, render_json_dev, render_basic
from .meta import MetaApplication, META_ASSETS_APP
from .static import StaticApplication, StaticFileRoute
from .errors import HTTPException, BadRequest, InternalServerError
from .utils import Redirector
from ._version import version_info, __version__

from werkzeug.wrappers import BaseRequest, Request, BaseResponse, Response
from werkzeug.utils import redirect, append_slash_redirect
