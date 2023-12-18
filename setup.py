# -*- coding: utf-8 -*-

"""Clastic is a functional Python web framework that streamlines
explicit development practices while eliminating global state.
"""

import os
import importlib
from setuptools import setup


__author__ = 'Mahmoud Hashemi'
__contact__ = 'mahmoud@hatnote.com'
__url__ = 'https://github.com/mahmoud/clastic'
__license__ = 'BSD'

def import_path(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

CUR_PATH = os.path.abspath(os.path.dirname(__file__))
_version_mod_path = os.path.join(CUR_PATH, 'clastic', '_version.py')
_version_mod = import_path('_version', _version_mod_path)
__version__ = _version_mod.__version__


desc = ('A functional Python web framework that streamlines'
        ' explicit development practices while eliminating'
        ' global state.')


setup(name='clastic',
      version=__version__,
      description=desc,
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=['clastic',
                'clastic.render',
                'clastic.middleware',
                'clastic.contrib',
                'clastic.tests'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'Werkzeug>=1.0.0,<2.0', 
          'ashes',
          'attrs',
          'boltons>=20.0.0', 
          'glom', 
          'secure-cookie==0.1.0,<=0.2.0'],
      license=__license__,
      platforms='any',
      tests_require=[
          'chameleon==3.9.1',
          'Mako', 
          'pytest', 
          'psutil'],
      classifiers=[
          'Intended Audience :: Developers',
          'Development Status :: 5 - Production/Stable',
          'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
          'Topic :: Internet :: WWW/HTTP :: WSGI',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          ]

      )

"""
A brief checklist for release:

* tox
* git commit (if applicable)
* Bump clastic/_version version off of -dev
* git commit -a -m "bump version for x.y.z release"
* rm -rf dist/*
* python setup.py sdist bdist_wheel
* twine upload dist/*
* bump docs/conf.py version
* write CHANGELOG
* git commit
* git tag -a x.y.z -m "brief summary"
* bump clastic/_version.py version onto n+1 dev
* git commit
* git push

"""
