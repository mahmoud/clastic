

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

    cl = app.get_local_client()
    resp = cl.get('/')
    assert 'hello' in resp.get_data(True)
