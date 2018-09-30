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
        'Django>=1.11,<2',
        'django-allauth>=0.28',
        'Markdown>=2.6,<3',
        'django-bootstrap4',
        'psycopg2-binary>=2.7,<3',
        'numpy',
        'beautifulsoup4',
        'natsort',
        'django-js-reverse',
        'pandas',
        'scipy>=1',
        'typing>=3.6,<4',
        'raven>=6.1.0,<7',
        'djangorestframework>=3.6,<4',
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
