# -*- coding: utf-8 -*-


from clastic import Application, render_basic, RerouteWSGI
from clastic.route import GET, POST, PUT, DELETE


def test_http_method_routes():
    ep = lambda _route: repr(_route.methods)
    routes = [GET('/get', ep, render_basic),
              POST('/post', ep, render_basic),
              PUT('/put', ep, render_basic),
              DELETE('/delete', ep, render_basic)]
    app = Application(routes)
    client = app.get_local_client()
    methods = ('get', 'post', 'put', 'delete')
    status_map = {}
    for correct_method in methods:
        for attempted_method in methods:
            req_func = getattr(client, attempted_method)
            resp = req_func('/' + correct_method)
            status_code = resp.status_code
            try:
                status_map[status_code] += 1
            except KeyError:
                status_map[status_code] = 1

            if status_code == 200:
                resp_data = resp.data
                # lololol yay eval()
                route_methods = eval(resp_data) - set(['HEAD'])
                assert set([correct_method.upper()]) == route_methods
    assert status_map[200] == len(routes)
    assert status_map.get(405) == len(routes) * (len(methods) - 1)
    return


def test_reroute_wsgi():
    # simulate home page served by one app, and all else by another
    other_app = Application([('/other', lambda: 'okay', render_basic)])
    main_app = Application([('/', lambda: 'hooray', render_basic),
                            ('/<x*str>', RerouteWSGI(other_app))])
    cl = main_app.get_local_client()
    resp = cl.get('/')
    assert resp.get_data(as_text=True) == 'hooray'

    resp = cl.get('/other/')
    assert resp.get_data(as_text=True) == 'okay'
