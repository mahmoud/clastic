# -*- coding: utf-8 -*-

"""Clastic is a functional Python web framework that streamlines
explicit development practices while eliminating global state.
"""

import sys
from setuptools import setup


__author__ = 'Mahmoud Hashemi'
__version__ = '19.0.0dev'
__contact__ = 'mahmoud@hatnote.com'
__url__ = 'https://github.com/mahmoud/clastic'
__license__ = 'BSD'

desc = ('A functional Python web framework that streamlines'
        ' explicit development practices while eliminating'
        ' global state.')

if sys.version_info < (2,6):
    raise NotImplementedError("Sorry, clastic only supports Python >=2.6")

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
      install_requires=['Werkzeug==0.14.1', 'argparse>=1.2.1', 'boltons', 'ashes', 'glom'],
      license=__license__,
      platforms='any',
      tests_require=['Mako==1.0.7', 'pytest==4.3.0', 'psutil==5.5.1'],
      classifiers=[
          'Intended Audience :: Developers',
          'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
          'Topic :: Internet :: WWW/HTTP :: WSGI',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
          'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7', ]
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
