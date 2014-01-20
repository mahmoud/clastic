# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from clastic.cline import route, run


@route('/')
@route('/<name>')
def hello_world(name='world'):
    return '<html><body><h1>Hello %s!</h1></body></html>' % name


if __name__ == '__main__':
    run()  # alt: run(address='0.0.0.0', port=5000)

    # run the script with `python this_script.py`
    # now visit http://localhost:5000/_meta in your browser to see a site map
    # resources like images/css can be served out of a directory called static
    # run the script with --help for more info
