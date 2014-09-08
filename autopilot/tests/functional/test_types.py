
from datetime import datetime, timedelta
import time

from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional import QmlScriptRunnerMixin
from dateutil.tz import tzlocal

from textwrap import dedent


class TypeTests(AutopilotTestCase, QmlScriptRunnerMixin):

    def test_date(self):
        proxy = self.start_qml_script(
            dedent(
                """\
                import QtQuick 2.0

                Item {
                    objectName: "TestMePlease"
                    property date foo: "2014-01-01"
                }
                """
            )
        )
        item = proxy.select_single('*', objectName="TestMePlease")
        dt = datetime(2014, 1, 1, 0, 0, 0, tzinfo=tzlocal())
        timestamp = time.mktime(dt.timetuple())
        dt = datetime.fromtimestamp(
            0, tz=tzlocal()) + timedelta(seconds=timestamp)
        self.assertEqual(
            item.foo,
            dt
        )
