#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='mangaki',
    description='Anime and manga recommendation website',
    author='Basile Clement, Ryan Lahfa and Jill-Jênn Vie',
    author_email='ryan@mangaki.fr',
    url='https://mangaki.fr',
    python_requires='>=3.4',
    install_requires=[
        'Django==2.1.2',
        'django-allauth==0.38',
        'Markdown==3.0.1',
        'django-bootstrap4',
        'psycopg2-binary',
        'numpy>=1.13',
        'beautifulsoup4',
        'natsort',
        'django-js-reverse==0.8.2',
        'pandas',
        'typing>=3.6,<4',
        'raven>=6.1.0,<7',
        'djangorestframework==3.8.2',
        'coreapi>=2.3,<3',
        'celery>=4.2,<5',
        'redis>=2.10,<3',
        'python-redis-lock>=3.2,<4',
        'django-celery-beat>=1.1,<2',
        'setuptools_scm>=1.15,<2',
        'django-sendfile>=0.3,<1'
    ],
    packages=find_packages(),
    include_package_data=True,
    use_scm_version={'root': '..'},
    setup_requires=['setuptools_scm'],
    zip_safe=False,
)
