from fixtures import EnvironmentVariable
from datetime import datetime

from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional import QmlScriptRunnerMixin

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
        self.assertEqual(
            item.foo,
            datetime(2014, 1, 1, 0, 0, 0)
        )


class DateTimeTests(AutopilotTestCase, QmlScriptRunnerMixin):
    scenarios = [
        ('UTC', dict(TZ='UTC')),
        ('NZ', dict(TZ='Pacific/Auckland')),
        ('US Central', dict(TZ='US/Central ')),
        ('US Eastern', dict(TZ='US/Eastern')),
    ]

    def test_comparisons_with_timezone(self):
        epoch_timestamp = 1411992000
        epoch_timestamp_milli = 1411992000000
        # epoch: 1411992000
        # epoch (milli): 1411992000000
        # UTC: Mon, 29 Sep 2014 12:00:00 GMT
        # Local (NZ): 30/9/2014 01:00:00 GMT+13
        qml_script = dedent("""
        import QtQuick 2.0
        import QtQml 2.2
        Rectangle {
            property date currentTime: new Date(1411992000000);
            Text {
                // Display (local time): 2014-09-30T01:00:00
                text: currentTime;
            }
        }""");
        self.useFixture(EnvironmentVariable('TZ', self.TZ))
        proxy = self.start_qml_script(qml_script)

        self.assertEqual(
            proxy.select_single("QQuickRectangle").currentTime,
            datetime.fromtimestamp(epoch_timestamp)
        )
        self.assertEqual(
            datetime.utcfromtimestamp(
                proxy.select_single("QQuickRectangle").currentTime.timestamp
            ),
            datetime.utcfromtimestamp(epoch_timestamp)
        )
