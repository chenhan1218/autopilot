# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

from fixtures import Fixture
import logging
import subprocess


logger = logging.getLogger(__name__)


class FixtureWithDirectAddDetail(Fixture):

    """A test fixture that has a 'caseAddDetail' method that corresponds
    to the addDetail method of the test case in use.

    You must derive from this class in order to add detail objects to tests
    from within cleanup actions.

    """

    def __init__(self, caseAddDetail=None):
        """Create the fixture.

        :param caseAddDetail: A closure over the testcase's addDetail
            method, or a similar substitution method. This may be omitted, in
            which case the 'caseAddDetail' method will be set to the fixtures
            normal 'addDetail' method.
        """
        super().__init__()
        self.caseAddDetail = caseAddDetail or self.addDetail


class OSKAlwaysEnabled(Fixture):
    """Enable the OSK to be shown regardless of if there is a keyboard (virtual
    or real) plugged in.

    This is a workaround for bug lp:1474444

    """

    osk_schema = 'com.canonical.keyboard.maliit'
    osk_show_key = 'stay-hidden'

    def __init__(self):
        super().__init__()
        self._original_value = get_gsettings_value(
            self.osk_schema,
            self.osk_show_key
        )

    def setUp(self):
        super().setUp()
        set_gsettings_value(self.osk_schema, self.osk_show_key, 'false')
        self.addCleanup(
            set_gsettings_value,
            self.osk_schema,
            self.osk_show_key,
            self._original_value
        )


def get_gsettings_value(schema, key):
    command = ['gsettings', 'get', schema, key]
    try:
        subprocess.check_output(command, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.warning(
            'Failed to get gsettings value for {schema}/{key}: {error}'.format(
                schema=schema, key=key, error=e.output
            )
        )


def set_gsettings_value(schema, key, value):
    command = ['gsettings', 'set', schema, key, value]
    try:
        subprocess.check_output(command, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.warning(
            'Failed to set gsettings value {sch}/{key} to {v}: {error}'.format(
                sch=schema, key=key, v=value, error=e.output
            )
        )
