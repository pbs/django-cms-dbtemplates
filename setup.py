#!/usr/bin/env python
import os
from setuptools import setup, find_packages

README_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'README.rst')

dependencies = [
]

dependency_links = [
    'http://github.com/pbs/django-dbtemplates/tarball/develop#egg=django-dbtemplates-1.4.1pbs',
    'http://github.com/pbs/django-cms/tarball/support/2.3.x#egg=django-cms-2.3.5pbs',
]



setup(
    name='django-cms-dbtemplates',
    version='0.3',
    description='Integrate django-cms and django-dbtemplates',
    long_description = open(README_PATH, 'r').read(),
    author='Sever Banesiu',
    author_email='banesiu.sever@gmail.com',
    url='https://github.com/pbs/django-cms-dbtemplates',
    packages = find_packages(),
    include_package_data=True,
    install_requires = dependencies,
    dependency_links = dependency_links,
    setup_requires = [
        'django-dbtemplates==1.4.1pbs',
        'django-cms==2.3.5pbs',
        's3sourceuploader',
    ],
    tests_require = [
        'django-nose',
        'djangotoolbox',
    ],
    test_suite = 'runtests.runtests',
)
