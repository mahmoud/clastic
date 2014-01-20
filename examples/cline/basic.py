# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from clastic.cline import route, run, get


@route('/')
@route('/hello/<name>')
def hello_world(name='world'):
    return '<html><body><h1>Hello %s!</h1></body></html>' % name


@route('/query_params')
def show_query_params(request):
    """to access the request, just add it to your parameters
    same goes for any other clastic builtins, like _route or _application
    """
    return dict(request.args)


@get('/path/<a_list*>')
def get_len_tuple(a_list):
    "note that clastic turns paths into lists"
    return (len(a_list), a_list)


if __name__ == '__main__':
    run()  # alt: run(address='0.0.0.0', port=5000)

    # run the script with `python this_script.py`
    # now visit http://localhost:5000/_meta in your browser to see a site map
    # resources like images/css can be served out of a directory called static
    # run the script with --help for more info
