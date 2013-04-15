#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

try:
    from debian import changelog
    chl = changelog.Changelog(open('debian/changelog'))
    version = str(chl.get_version())
except ImportError:
    # If we don't have python-debian installed, guess a coarse-grained version string
    version = '1.3'

setup(
    name='autopilot',
    version=version,
    description='Functional testing tool for Ubuntu.',
    author='Thomi Richards',
    author_email='thomi.richards@canonical.com',
    url='https://launchpad.net/autopilot',
    license='GPLv3',
    packages=find_packages(),
    test_suite='autopilot.tests',
    scripts=['bin/autopilot',],
)

