
from werkzeug.test import Client

from clastic import Response
from clastic.cline import Cline

def test_cline():
    app = Cline()

    @app.get('/')
    @app.post('/')
    @app.put('/')
    @app.delete('/')
    @app.patch('/')
    @app.head('/')
    def hw():
        return 'hello, world'

    cl = Client(app, Response)
    resp = cl.get('/')
    assert 'hello' in resp.get_data(True)
