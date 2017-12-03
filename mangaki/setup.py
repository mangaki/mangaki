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
        'django-bootstrap3>=8.2,<9',
        'psycopg2>=2.7,<3',
        'numpy',
        'beautifulsoup4',
        'natsort',
        'django-analytical',
        'django-cookie-law',
        'django-js-reverse',
        'scikit-learn>=0.18,<0.19',
        'scipy',
        'pandas',
        'typing>=3.6,<4',
        'tensorflow>=1.1.0,<1.2',
        'raven>=6.1.0,<7',
        'djangorestframework>=3.6,<4',
        'coreapi>=2.3,<3',
        'celery>=4.0,<5',
        'redis>=2.10,<3',
        'Pillow>=4.1,<5',
        'setuptools_scm>=1.15,<2'
    ],
    packages=find_packages(),
    include_package_data=True,
    use_scm_version={'root': '..'},
    setup_requires=['setuptools_scm'],
    zip_safe=False,
)
