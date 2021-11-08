# -*- coding: utf-8 -*-

"""Clastic is a functional Python web framework that streamlines
explicit development practices while eliminating global state.
"""

import os
import imp
import sys
from setuptools import setup


__author__ = 'Mahmoud Hashemi'
__contact__ = 'mahmoud@hatnote.com'
__url__ = 'https://github.com/mahmoud/clastic'
__license__ = 'BSD'

CUR_PATH = os.path.abspath(os.path.dirname(__file__))
_version_mod_path = os.path.join(CUR_PATH, 'clastic', '_version.py')
_version_mod = imp.load_source('_version', _version_mod_path)
__version__ = _version_mod.__version__


desc = ('A functional Python web framework that streamlines'
        ' explicit development practices while eliminating'
        ' global state.')

if sys.version_info < (2,6):
    raise NotImplementedError("Sorry, clastic only supports Python >2.6")

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
      install_requires=['Werkzeug>=1.0.0,<2.0', 'boltons>=20.0.0', 'ashes', 'glom', 'secure-cookie'],
      license=__license__,
      platforms='any',
      tests_require=['Mako==1.0.7', 'pytest==4.6.9', 'psutil==5.8.0'],
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
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10']

      )

"""
A brief checklist for release:

* tox
* git commit (if applicable)
* Bump setup.py version off of -dev
* git commit -a -m "bump version for x.y.z release"
* python setup.py sdist bdist_wheel upload
* git tag -a x.y.z -m "brief summary"
* write CHANGELOG
* git commit
* bump setup.py version onto n+1 dev
* git commit
* git push

"""
