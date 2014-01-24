#!/bin/sh
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

if [ "$1" = "-h" ]; then
	echo "usage: $0 [-h] [-n]"
	echo
	echo "Runs unit tests under both python2 and python 3, gathering coverage data."
	echo "By default, will open HTML coverage report in the default browser. If -n"
	echo "is specified, will re-generate coverage data, but won't open the browser."
	exit 0
fi

if [ -d htmlcov ]; then
	rm -r htmlcov
fi
python -m coverage erase
python -m coverage run --branch --include "autopilot/*" -m autopilot.run run autopilot.tests.unit
python3 -m coverage run --append --branch --include "autopilot/*" -m autopilot.run run autopilot.tests.unit
python -m coverage html --omit "autopilot/tests/*"

if [ "$1" != "-n" ]; then
	xdg-open htmlcov/index.html
fi
