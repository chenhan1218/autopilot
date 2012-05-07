#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

setup(
    name='autopilot',
    version='1.0',
    description='Functional testing tool for Ubuntu.',
    author='Thomi Richards',
    author_email='thomi.richards@canonical.com',
    url='https://launchpad.net/autopilot',
    license='GPLv3',
    packages=find_packages(),
    test_suite='tests',
    scripts='bin/autopilot',
)

