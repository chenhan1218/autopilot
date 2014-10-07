# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
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

from datetime import datetime
from fixtures import EnvironmentVariable

from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional import QmlScriptRunnerMixin

from textwrap import dedent


class DateTimeTests(AutopilotTestCase, QmlScriptRunnerMixin):
    scenarios = [
        ('UTC', dict(
            TZ='UTC',
            expected_string='2014-09-29T12:00:00',
        )),
        ('NZ', dict(
            TZ='Pacific/Auckland',
            expected_string='2014-09-30T01:00:00',
        )),
        ('US Central', dict(
            TZ='US/Central',
            expected_string='2014-09-29T07:00:00',
        )),
        ('US Eastern', dict(
            TZ='US/Eastern',
            expected_string='2014-09-29T08:00:00',
        )),
        ('MSK', dict(
            TZ='Europe/Moscow',
            expected_string='2014-09-29T16:00:00',
        )),
    ]

    def get_test_qml_string(self, date_string):
        return dedent("""
            import QtQuick 2.0
            import QtQml 2.2
            Rectangle {
                property date testingTime: new Date(%s);
                Text {
                    text: testingTime;
                }
            }""" % date_string)

    def set_testing_timezone(self):
        import time as _time
        self.addCleanup(_time.tzset)
        self.useFixture(EnvironmentVariable('TZ', self.TZ))
        _time.tzset()

    def test_qml_applies_timezone_to_timestamp(self):
        """Test that when given a timestamp the datetime displayed has the
        timezone applied to it.

        QML will apply a timezone calculation to a timestamp (but not a
        timestring).

        """
        self.set_testing_timezone()
        qml_script = self.get_test_qml_string('1411992000000')

        proxy = self.start_qml_script(qml_script)
        self.assertEqual(
            proxy.select_single('QQuickText').text,
            self.expected_string
        )

    def test_timezone_not_applied_to_timestring(self):
        self.set_testing_timezone()

        qml_script = self.get_test_qml_string("'2014-01-15 12:34:52'")
        proxy = self.start_qml_script(qml_script)
        date_object = proxy.select_single("QQuickRectangle").testingTime

        self.assertEqual(date_object.year, 2014)
        self.assertEqual(date_object.month, 1)
        self.assertEqual(date_object.day, 15)
        self.assertEqual(date_object.hour, 12)
        self.assertEqual(date_object.minute, 34)
        self.assertEqual(date_object.second, 52)
        self.assertEqual(datetime(2014, 1, 15, 12, 34, 52), date_object)
