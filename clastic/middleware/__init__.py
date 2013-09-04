# -*- coding: utf-8 -*-

from .core import (Middleware,
                   check_middlewares,
                   merge_middlewares,
                   make_middleware_chain,
                   DummyMiddleware)
from .url import GetParamMiddleware
from .context import (ContextProcessor,
                      SimpleContextProcessor)
from .compress import GzipMiddleware
from .profile import SimpleProfileMiddleware
from .client_cache import HTTPCacheMiddleware
