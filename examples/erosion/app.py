# -*- coding: utf-8 -*-

import os
import sys


_CUR_PATH = os.path.dirname(os.path.abspath(__file__))
_CLASTIC_PATH = os.path.dirname(os.path.dirname(_CUR_PATH))
sys.path.append(_CLASTIC_PATH)

try:
    import clastic
except ImportError:
    print "make sure you've got werkzeug and other dependencies installed"

from clastic import Application, POST, redirect
from clastic.errors import Forbidden
from clastic.render import AshesRenderFactory
from clastic.middleware import SimpleContextProcessor
from clastic.middleware.form import PostDataMiddleware
from clastic.middleware.session import CookieSessionMiddleware

# TODO: yell if static hosting is the same location as the application assets

from link_map import LinkMap
_DEFAULT_LINKS_FILE_PATH = os.path.join(_CUR_PATH, 'links.txt')


def home():
    return {}


def add_entry(link_map, target_url, target_file, alias,
              expiry_time, max_count):
    target = target_url or target_file
    if not target:
        raise ValueError('expected one of target url or file')
    entry = link_map.add_entry(target, alias, expiry_time, max_count)
    return {'entry': entry}


def add_entry_render(context, link_map):
    print 'yay', context
    link_map.save()
    return redirect('/', code=303)


def get_entry(link_map, alias, request, local_static_app=None):
    try:
        entry = link_map.get_entry(alias)
    except KeyError:
        return Forbidden()  # 404? 402?
    target_location = entry.target
    if target_location.startswith('/'):
        if local_static_app:
            return local_static_app.get_file_response(target, request)
        return Forbidden()
    else:
        return redirect('http://' + target_location, code=301)


def create_app(link_list_path=None, local_root=None):
    link_list_path = link_list_path or _DEFAULT_LINKS_FILE_PATH
    link_map = LinkMap(link_list_path)
    resources = {'link_map': link_map, 'local_root': local_root}

    pdm = PostDataMiddleware({'target_url': unicode,
                              'target_file': unicode,
                              'alias': unicode,
                              'max_count': int,
                              'expiry_time': unicode})
    submit_route = POST('/submit', add_entry, add_entry_render)
    submit_route._middlewares.append(pdm)

    routes = [('/', home, 'home.html'),
              submit_route,
              ('/<path:alias>', get_entry)]
    csm = CookieSessionMiddleware()
    scp = SimpleContextProcessor('local_root')

    arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
    app = Application(routes, resources, arf, [csm, scp])
    return app


def main():
    app = create_app(local_root='/tmp/')
    app.serve()


if __name__ == '__main__':
    main()
