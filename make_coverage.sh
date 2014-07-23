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

set -e

SHOW_IN_BROWSER="yes"
INCLUDE_TEST_FILES="no"
TEST_SUITE_TO_RUN="autopilot.tests.unit"

usage() {
	echo "usage: $0 [-h] [-n] [-t] [-s suite]"
	echo
	echo "Runs unit tests under python 3, gathering coverage data."
    echo
	echo "By default, will open HTML coverage report in the default browser. If -n"
	echo "is specified, will re-generate coverage data, but won't open the browser."
    echo
    echo "If -t is specified the HTML coverage report will include the test files."
    echo
    echo "If -s is specified, the next argument must be a test id to run. If not"
    echo "specified, the default is '$TEST_SUITE_TO_RUN'."
}

while getopts ":hnts:" o; do
    case "${o}" in
        n)
            SHOW_IN_BROWSER="no"
            ;;
        t)
            INCLUDE_TEST_FILES="yes"
            ;;
        s)
            TEST_SUITE_TO_RUN=$OPTARG
            ;;
        *)
            usage
            exit 0
            ;;
    esac
done

if [ -d htmlcov ]; then
	rm -r htmlcov
fi

python3 -m coverage erase
python3 -m coverage run --append --branch --include "autopilot/*" -m autopilot.run run $TEST_SUITE_TO_RUN

if [ "$INCLUDE_TEST_FILES" = "yes" ]; then
    python3 -m coverage html
else
    python3 -m coverage html --omit "autopilot/tests/*"
fi

if [ "$SHOW_IN_BROWSER" = "yes" ]; then
	xdg-open htmlcov/index.html
fi
