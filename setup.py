#!/usr/bin/env python
import os
from setuptools import setup, find_packages

README_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'README.rst')

dependencies = [
    'django-dbtemplates',
    'django-cms',
]

dependency_links = [
]

setup(
    name='django-cms-dbtemplates',
    version='0.1',
    description='Integrate django-cms and django-dbtemplates',
    long_description = open(README_PATH, 'r').read(),
    author='Sever Banesiu',
    author_email='banesiu.sever@gmail.com',
    url='https://github.com/pbs/django-cms-dbtemplates',
    packages = find_packages(),
    include_package_data=True,
    install_requires = dependencies,
    dependency_links = dependency_links,
)
