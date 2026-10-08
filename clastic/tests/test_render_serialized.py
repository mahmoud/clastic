import pytest

from clastic import Application
from clastic.render import render_basic


@pytest.mark.parametrize('content, mimetype', [
    ('{}', 'application/json'),
    ('[]', 'application/json'),
    ('{"name": "caf\u00e9"}', 'application/json'),
    ('[1, 2]', 'application/json'),
    ('', 'text/plain'),
    ('{', 'text/plain'),
    ('[', 'text/plain'),
    ('{]', 'text/plain'),
    ('plain text', 'text/plain'),
    ('<html>hello</html>', 'text/html'),
])
@pytest.mark.parametrize('as_bytes', [False, True])
def test_serialized_response_content_type(content, mimetype, as_bytes):
    payload = content.encode('utf-8') if as_bytes else content

    def endpoint():
        return payload

    app = Application([('/', endpoint, render_basic)])
    response = app.get_local_client().get('/')
    assert response.status_code == 200
    assert response.mimetype == mimetype
    assert response.data == content.encode('utf-8')
