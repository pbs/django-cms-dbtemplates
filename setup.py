#!/usr/bin/env python
import os
from setuptools import setup, find_packages

README_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'README.rst')

dependencies = [
    'django-cms>=2.3.5pbs, <2.3.6',
    'djangotoolbox',
    'django-dbtemplates>=1.4.1pbs, <1.5',
    'python-graph-core',
    'django-admin-extend',
]


dependency_links = [
    'http://github.com/pbs/django-dbtemplates/tarball/develop#egg=django-dbtemplates-1.4.1pbs.X.dev',
    'http://github.com/pbs/django-cms/tarball/support/2.3.x#egg=django-cms-2.3.5pbs.X.dev',
    'http://github.com/pbs/django-admin-extend/tarball/master#egg=django-admin-extend-dev',
]


setup(
    name='django-cms-dbtemplates',
    version='1.3.1',
    description='Integrate django-cms and django-dbtemplates',
    long_description=open(README_PATH, 'r').read(),
    author='Sever Banesiu',
    author_email='banesiu.sever@gmail.com',
    url='https://github.com/pbs/django-cms-dbtemplates',
    packages=find_packages(),
    include_package_data=True,
    install_requires=dependencies,
    dependency_links=dependency_links,
)
