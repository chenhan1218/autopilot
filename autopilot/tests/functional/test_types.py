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
        ('UTC', dict(
            TZ='UTC',
            expected_string='2014-09-29T12:00:00',
            expected_datetime = dict(day=29, hour=12),
        )),
        ('NZ', dict(
            TZ='Pacific/Auckland',
            expected_string='2014-09-30T01:00:00',
            expected_datetime = dict(day=30, hour=1),
        )),
        ('US Central', dict(
            TZ='US/Central',
            expected_string='2014-09-29T07:00:00',
            expected_datetime = dict(day=29, hour=7),
        )),
        ('US Eastern', dict(
            TZ='US/Eastern',
            expected_string='2014-09-29T08:00:00',
            expected_datetime = dict(day=29, hour=8),
        )),
    ]

    def test_qml_provides_in_localtime(self):
        qml_script = dedent("""
            import QtQuick 2.0
            import QtQml 2.2
            Rectangle {
                property date testingTime: new Date(1411992000000);
                Text {
                    text: testingTime;
                }
            }""");
        self.useFixture(EnvironmentVariable('TZ', self.TZ))
        proxy = self.start_qml_script(qml_script)
        self.assertEqual(
            proxy.select_single('QQuickText').text,
            self.expected_string
        )

    def test_localtime_always_provided(self):
        qml_script = dedent("""
            import QtQuick 2.0
            import QtQml 2.2
            Rectangle {
                property date testingTime: new Date('2014-01-15 12:34:52');
                Text {
                    text: testingTime;
                }
            }""");
        self.useFixture(EnvironmentVariable('TZ', self.TZ))
        proxy = self.start_qml_script(qml_script)
        date_object = proxy.select_single("QQuickRectangle").testingTime

        self.assertEqual(date_object.year, 2014)
        self.assertEqual(date_object.month, 1)
        self.assertEqual(date_object.day, 15)
        self.assertEqual(date_object.hour, 12)
        self.assertEqual(date_object.minute, 34)
        self.assertEqual(date_object.second, 52)
        self.assertEqual(
            datetime.strptime('2014-01-15 12:34:52', '%Y-%m-%d %H:%M:%S'),
            date_object
        )

    def test_comparisons_with_timezone(self):
        epoch_timestamp = 1411992000
        epoch_timestamp_milli = 1411992000000
        qml_script = dedent("""
        import QtQuick 2.0
        import QtQml 2.2
        Rectangle {
            property date testingTime: new Date(1411992000000);
            Text {
                text: testingTime;
            }
        }""");
        self.useFixture(EnvironmentVariable('TZ', self.TZ))
        proxy = self.start_qml_script(qml_script)

        date_object = proxy.select_single("QQuickRectangle").testingTime
        self.assertEqual(date_object.day, self.expected_datetime['day'])
        self.assertEqual(date_object.hour, self.expected_datetime['hour'])
