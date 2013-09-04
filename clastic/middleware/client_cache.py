# -*- coding: utf-8 -*-


from .core import Middleware


class HTTPCacheMiddleware(Middleware):
    cache_attrs = ('max_age', 's_maxage', 'no_cache', 'no_store',
                   'no_transform', 'must_revalidate', 'proxy_revalidate',
                   'public', 'private')
    def __init__(self,
                 max_age=None,
                 s_maxage=None,
                 no_cache=None,
                 no_store=None,
                 no_transform=None,
                 must_revalidate=None,
                 proxy_revalidate=None,
                 public=None,
                 private=None,
                 use_etags=True):
        for attr in self.cache_attrs:
            setattr(self, attr, locals()[attr])
        self.use_etags = use_etags

    def request(self, next, request):
        resp = next()
        if hasattr(resp, 'cache_control'):
            for attr in self.cache_attrs:
                cache_val = getattr(self, attr, None)
                if cache_val:
                    setattr(resp.cache_control, attr, cache_val)
            if self.use_etags and not resp.is_streamed:
                # TODO: do streamed responses too?
                resp.add_etag()
                resp.make_conditional(request)
        return resp
