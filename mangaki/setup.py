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
        'django-bootstrap3>=8.2,<8.3',
        'psycopg2>=2.7,<3',
        'numpy',
        'beautifulsoup4',
        'natsort',
        'django-analytical',
        'django-cookie-law',
        'django-js-reverse',
        'djangorestframework',
        'scikit-learn>=0.18,<0.19',
        'scipy',
        'pandas',
        'typing>=3.6,<3.7',
        'tensorflow>=1.1.0,<1.2',
        'raven>=6.1.0',
        'djangorestframework>=3.6,<3.7',
        'coreapi>=2.3,<2.4',
        'celery>=4.0,<4.1',
        'redis>=2.10,<2.11',
        'Pillow>=4.1',
        'setuptools_scm>=1.15'
    ],
    packages=find_packages(),
    include_package_data=True,
    use_scm_version={'root': '..'},
    setup_requires=['setuptools_scm'],
    zip_safe=False,
)
