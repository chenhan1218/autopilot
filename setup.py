#!/usr/bin/env python

#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


from setuptools import find_packages, setup, Extension


VERSION = '1.4.0'


autopilot_tracepoint = Extension(
    'autopilot.tracepoint',
    libraries=['lttng-ust'],
    include_dirs=['lttng_module'],
    sources=['lttng_module/autopilot_tracepoint.c']
)

setup(
    name='autopilot',
    version=VERSION,
    description='Functional testing tool for Ubuntu.',
    author='Thomi Richards',
    author_email='thomi.richards@canonical.com',
    url='https://launchpad.net/autopilot',
    license='GPLv3',
    packages=find_packages(),
    test_suite='autopilot.tests',
    scripts=['bin/autopilot', 'bin/autopilot-sandbox-run'],
    ext_modules=[autopilot_tracepoint],
)
