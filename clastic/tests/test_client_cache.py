import pytest

from clastic import Application, Response
from clastic.middleware.client_cache import HTTPCacheMiddleware


@pytest.mark.parametrize('attribute', ['max_age', 's_maxage'])
@pytest.mark.parametrize('initial', [None, 3600])
def test_zero_cache_lifetime(attribute, initial):
    def endpoint():
        response = Response('cached content')
        if initial is not None:
            setattr(response.cache_control, attribute, initial)
        return response

    app = Application([('/', endpoint)], middlewares=[
        HTTPCacheMiddleware(use_etags=False, **{attribute: 0})])
    response = app.get_local_client().get('/')
    assert response.status_code == 200
    assert response.cache_control[attribute.replace('_', '-')] == '0'


@pytest.mark.parametrize('attribute', [
    'no_cache', 'no_store', 'no_transform', 'must_revalidate',
    'proxy_revalidate', 'public', 'private'])
def test_explicit_false_removes_cache_directive(attribute):
    def endpoint():
        response = Response('cached content')
        setattr(response.cache_control, attribute, True)
        return response

    app = Application([('/', endpoint)], middlewares=[
        HTTPCacheMiddleware(use_etags=False, **{attribute: False})])
    response = app.get_local_client().get('/')
    assert not getattr(response.cache_control, attribute)


def test_unspecified_cache_settings_preserve_endpoint_values():
    def endpoint():
        response = Response('cached content')
        response.cache_control.max_age = 3600
        response.cache_control.public = True
        return response

    app = Application([('/', endpoint)], middlewares=[
        HTTPCacheMiddleware(use_etags=False)])
    response = app.get_local_client().get('/')
    assert response.cache_control.max_age == 3600
    assert response.cache_control.public is True
