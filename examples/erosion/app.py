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
from clastic.static import StaticApplication
from clastic.render import AshesRenderFactory
from clastic.middleware import SimpleContextProcessor
from clastic.middleware.form import PostDataMiddleware
from clastic.middleware.cookie import SignedCookieMiddleware


from link_map import LinkMap
_DEFAULT_LINKS_FILE_PATH = os.path.join(_CUR_PATH, 'links.txt')


def home(link_map, cookie):
    new_entry_alias = cookie.pop('new_entry_alias', None)
    aliases = cookie.get('aliases', [])
    entries, expired = [], []
    for a in aliases:
        try:
            entries.append(link_map.get_entry(a).to_dict())
        except:
            expired.append(a)
    return {'new_entry_alias': new_entry_alias,
            'entries': entries,
            'expired': expired}


def add_entry(link_map, target_url, target_file, alias,
              expiry_time, max_count):
    if target_file:
        target = '/' + target_file.strip('/')
    elif target_url:
        if '://' not in target_url[:10]:
            target_url = 'http://' + target_url
        target = target_url
    else:
        raise ValueError('expected one of target url or file')
    entry = link_map.add_entry(target, alias, expiry_time, max_count)
    link_map.save()
    return {'new_entry': entry}


def add_entry_render(context, cookie, link_map):
    new_entry = context.get('new_entry')
    if new_entry:
        cookie['new_entry_alias'] = new_entry.alias
        cookie.setdefault('aliases', []).insert(0, new_entry.alias)
    return redirect('/', code=303)


def use_entry(link_map, alias, request, local_static_app=None):
    entry = link_map.use_entry(alias)
    if not entry:
        return Forbidden(is_breaking=False)  # 404? 402?
    target = entry.target
    if target.startswith('/'):
        if local_static_app:
            rel_path = target[1:]
            link_map.save()
            return local_static_app.get_file_response(rel_path, request)
        else:
            m = 'This Erosion instance is not configured to host local files.'
            return Forbidden(m, is_breaking=False)
    else:
        link_map.save()
        return redirect(target, code=301)


def create_app(link_list_path=None, local_root=None, host_url=None,
               secret_key=None):
    link_list_path = link_list_path or _DEFAULT_LINKS_FILE_PATH
    link_map = LinkMap(link_list_path)
    local_static_app = None
    if local_root:
        local_static_app = StaticApplication(local_root)
    host_url = (host_url or 'localhost:5000').rstrip('/') + '/'
    full_host_url = 'http://' + host_url
    resources = {'link_map': link_map,
                 'local_root': local_root,
                 'local_static_app': local_static_app,
                 'host_url': host_url,
                 'full_host_url': full_host_url}

    pdm = PostDataMiddleware({'target_url': unicode,
                              'target_file': unicode,
                              'alias': unicode,
                              'max_count': int,
                              'expiry_time': unicode})
    submit_route = POST('/submit', add_entry, add_entry_render,
                        middlewares=[pdm])

    routes = [('/', home, 'home.html'),
              submit_route,
              ('/<alias>', use_entry)]
    scm = SignedCookieMiddleware(secret_key=secret_key)
    scp = SimpleContextProcessor('local_root', 'full_host_url')
    middlewares = [scm, scp]

    arf = AshesRenderFactory(_CUR_PATH, keep_whitespace=False)
    app = Application(routes, resources, middlewares, arf)
    return app


def main():
    secret_key = 'configurationmanagementisimportant'
    secret_key += os.getenv('EROSION_KEY') or 'really'
    app = create_app(local_root='/tmp/', secret_key=secret_key)
    app.serve(threaded=True)


if __name__ == '__main__':
    main()
