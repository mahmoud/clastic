import clastic

def hello_world():
    return clastic.Response("Hello, World")

def test_create_empty_application():
    app = clastic.Application()
    return app

def test_create_hw_application():
    route = ('/', hello_world)
    app = clastic.Application([route])
    assert app.routes
    assert callable(app.routes[0]._execute)
    assert app.routes[0]._bound_apps[0] is app
    return app
