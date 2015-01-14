Writing Good Autopilot Tests
============================

This document is an introduction to writing good autopilot tests. This should be treated as additional material on top of all the things you'd normally do to write good code. Put another way: test code follows all the same rules as production code - it must follow the coding standards, and be of a professional quality.

Several points in this document are written with respect to the unity autopilot test suite. This is incidental, and doesn't mean that these points do not apply to other test suites!

.. _write-expressive-tests:

Write Expressive Tests
++++++++++++++++++++++

Unit tests are often used as a reference for how your public API should be used. Functional (Autopilot) tests are no different: they can be used to figure out how your application should work from a functional standpoint. However, this only works if your tests are written in a clear, concise, and most importantly expressive style. There are many things you can do to make your tests easier to read:

**Pick Good Test Case Class Names**

Pick a name that encapsulates all the tests in the class, but is as specific as possible. If necessary, break your tests into several classes, so your class names can be more specific. This is important because when a test fails, the test id is the primary means of identifying the failure. The more descriptive the test id is, the easier it is to find the fault and fix the test.

**Pick Good Test Case Method Names**

Similar to picking good test case class names, picking good method names makes your test id more descriptive. We recommend writing very long test method names, for example:

.. code-block:: python

    # bad example:
    def test_save_dialog(self):
        # test goes here

    # better example:
    def test_save_dialog_can_cancel(self):
        # test goes here

    # best example:
    def test_save_dialog_cancels_on_escape_key(self):
        # test goes here

**Write Docstrings**

You should write docstrings for your tests. Often the test method is enough to describe what the test does, but an English description is still useful when reading the test code. For example:

.. code-block:: python

    def test_save_dialog_cancels_on_escape_key(self):
        """The Save dialog box must cancel when the escape key is pressed."""

We recommend following :pep:`257` when writing all docstrings.


Test One Thing Only
+++++++++++++++++++

Tests should test one thing, and one thing only. Since we're not writing unit tests, it's fine to have more than one assert statement in a test, but the test should test one feature only. How do you tell if you're testing more than one thing? There's two primary ways:

 1. Can you describe the test in a single sentence without using words like 'and', 'also', etc? If not, you should consider splitting your tests into multiple smaller tests.

 2. Tests usually follow a simple pattern:

  a. Set up the test environment.
  b. Perform some action.
  c. Test things with assert statements.

  If you feel you're repeating steps 'b' and 'c' you're likely testing more than one thing, and should consider splitting your tests up.

**Good Example:**

.. code-block:: python

    def test_alt_f4_close_dash(self):
        """Dash must close on alt+F4."""
        self.dash.ensure_visible()
        self.keyboard.press_and_release("Alt+F4")
        self.assertThat(self.dash.visible, Eventually(Equals(False)))

This test tests one thing only. Its three lines match perfectly with the typical three stages of a test (see above), and it only tests for things that it's supposed to. Remember that it's fine to assume that other parts of unity work as expected, as long as they're covered by an autopilot test somewhere else - that's why we don't need to verify that the dash really did open when we called ``self.dash.ensure_visible()``.

Fail Well
+++++++++

Make sure your tests test what they're supposed to. It's very easy to write a test that passes. It's much more difficult to write a test that only passes when the feature it's testing is working correctly, and fails otherwise. There are two main ways to achieve this:

* Write the test first. This is easy to do if you're trying to fix a bug in Unity. In fact, having a test that's exploitable via an autopilot test will help you fix the bug as well. Once you think you have fixed the bug, make sure the autopilot test you wrote now passed. The general workflow will be:

 0. Branch unity trunk.
 1. Write autopilot test that reproduces the bug.
 2. Commit.
 3. Write code that fixes the bug.
 4. Verify that the test now passes.
 5. Commit. Push. Merge.
 6. Celebrate!

* If you're writing tests for a bug-fix that's already been written but is waiting on tests before it can be merged, the workflow is similar but slightly different:

 0. Branch unity trunk.
 1. Write autopilot test that reproduces the bug.
 2. Commit.
 3. Merge code that supposedly fixes the bug.
 4. Verify that the test now passes.
 5. Commit. Push. Superseed original merge proposal with your branch.
 6. Celebrate!

Think about design
++++++++++++++++++
Much in the same way you might choose a functional or objective-oriented paradigm for a piece of code, a testsuite can benefit from choosing a good design pattern. One such design pattern is the page object model. The page object model can reduce testcase complexity and allow the testcase to grow and easily adapt to changes within the underlying application.

Introducing the Page Object Pattern
-----------------------------------
Automated testing of an application through the Graphical User Interface (GUI) is inherently fragile.
These tests require regular review and attention during the development cycle. This is known as *Interface Sensitivity ("even minor changes to the interface can cause tests to fail" [1])*.
Utilizing the page-object pattern, alleviates some of the problems stemming from this fragility, allowing us to do automated user acceptance testing (UAT) in a sustainable manner.

The Page Object Pattern comes from the Selenium community [2] and is the
best way to turn a flaky and unmaintainable user acceptance test into a stable and useful
part of your release process. A page is what's visible on the screen at a single moment.
A user story consists of a user jumping from page to page until they achieve there goal.
Thus pages are modeled as objects following these guidelines:

#. The public methods represent the services that the page offers.
#. Try not to expose the internals of the page.
#. Methods return other PageObjects.
#. Generally don't make assertions.
#. Objects need not represent the entire page.
#. Different results for the same action are modelled as different
   methods.

Lets take the page objects of the `Ubuntu Clock App  <http://bazaar.launchpad.net/~ubuntu-clock-dev/ubuntu-clock-app/trunk/view/399/tests/autopilot/ubuntu_clock_app/emulators.py>`__ as an example, with some simplifications. This application is written in
QML and Javascript using the `Ubuntu SDK <http://developer.ubuntu.com/apps/sdk/>`__.

1. The public methods represent the services that the page offers.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This application has a stopwatch page that lets users measure elapsed
time. It offers services to start, stop and reset the watch, so we start
by defining the stop watch page object as follows:

.. code-block:: python

    class Stopwatch(object):

        def start(self):
            raise NotImplementedError()

        def stop(self):
            raise NotImplementedError()

        def reset(self):
            raise NotImplementedError()

2. Try not to expose the internals of the page.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The internals of the page are more likely to change than the services it
offers. A stopwatch will keep the same three services we defined above
even if the whole design changes. In this case, we reset the stop watch
by clicking a button on the bottom-left of the window, but we hide that
as an implementation detail behind the public methods. In Python, we can
indicate that a method is for internal use only by adding a single
leading underscore to its name. So, lets implement the reset\_stopwatch
method:

.. code-block:: python

    def reset(self):
        self._click_reset_button()

    def _click_reset_button(self):
        reset_button = self.wait_select_single(
            'ImageButton', objectName='resetButton')
        self.pointing_device.click_object(reset_button)

Now if the designers go crazy and decide that it's better to reset the
stop watch in a different way, we will have to make the change only in
one place to keep all the tests working. Remember that this type of
tests has Interface Sensitivity, that's unavoidable; but we can reduce
the impact of interface changes with proper encapsulation and turn these
tests into a useful way to verify that a change in the GUI didn't
introduce any regressions.

3. Methods return other PageObjects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An UAT checks a user story. It will involve the journey of the user
through the system, so he will move from one page to another. Lets take
a look at how a journey to reset the stop watch will look like:

.. code-block:: python

    stopwatch = clock_page.open_stopwatch()
    stopwatch.start()
    stopwatch.reset()

In our sample application, the first page that the user will encounter
is the Clock. One of the things the user can do from this page is to
open the stopwatch page, so we model that as a service that the Clock
page provides. Then return the new page object that will be visible to
the user after completing that step.

.. code-block:: python

    class Clock(object):

        def open_stopwatch(self):
            self._switch_to_tab('StopwatchTab')
            return self.wait_select_single(Stopwatch)

Now the return value of open\_stopwatch will make available to the
caller all the available services that the stopwatch exposes to the
user. Thus it can be chained as a user journey from one page to the
other.

4. Generally don't make assertions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A well written UAT (user acceptance test) consists of a sequence of
steps or user actions and ends with one single assertion that verifies
that the user achieved its goal. The page objects are the helpers for
the user actions part of the test, so it's better to leave the check for
success out of them. With that in mind, a test for the reset of the
stopwatch would look like this:

.. code-block:: python

    def test_restart_button_must_restart_stopwatch_time(self):
        # Set up.
        stopwatch = self.clock_page.open_stopwatch()

        stopwatch.start()
        stopwatch.reset_stopwatch()

        # Check that the stopwatch has been reset.
        self.assertThat(
            stopwatch.get_time,
            Eventually(Equals('00:00.0')))

We have to add a new method to the stopwatch page object: get\_time. But
it only returns the state of the GUI as the user sees it. We leave in
the test method the assertion that checks it's the expected value.

.. code-block:: python

    class Stopwatch(object):

        ...

        def get_time(self):
            return self.wait_select_single(
                'Label', objectName='time').text

5. Need not represent an entire page
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The objects we are modeling here can just represent a part of the page.
Then we build the entire page that the user is seeing by composition of
page parts. This way we can reuse test code for parts of the GUI that
are reused in the application or between different applications. As an
example, take the \_switch\_to\_tab('StopwatchTab') method that we are
using to open the stopwatch page. The Clock application is using the
Header component provided by the Ubuntu SDK, as all the other Ubuntu
applications are doing too. So, the Ubuntu SDK also provides helpers to
make it easier the user acceptance testing of the applications, and you
will find an object like this:

.. code-block:: python

    class Header(object):

        def switch_to_tab(tab_object_name):
            """Open a tab.

            :parameter tab_object_name: The QML objectName property of the tab.
            :return: The newly opened tab.
            :raise ToolkitException: If there is no tab with that object
                name.

            """
        ...

This object just represents the header of the page, and inside the
object we define the services that the header provides to the users. If
you dig into the full implementation of the Clock test class you will
find that in order to open the stopwatch page we end up calling Header
methods.

6. Different results for the same action are modeled as different methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

According to the guideline #3 we are returning page objects every time
that a user action opens the option for new actions to execute.
Sometimes the same action has different results depending on the context
or the values used for the action. For example, the Clock app has an
Alarm page. In this page you can add new alarms, but if you try to add
an alarm for sometime in the past, it will result in an error. So, we
will have two different tests that will look something like this:

.. code-block:: python

    def test_add_alarm_for_tomorrow_must_add_to_alarm_list(self):
        tomorrow = ...
        test_alarm_name = 'Test alarm for tomorrow'
        alarm_page = self.alarm_page.add_alarm(
            test_alarm_name, tomorrow)

        saved_alarms = alarm_page.get_saved_alarms()
        self.assertIn(
            (test_alarm_name, tomorrow),
            saved_alarms)

    def test_add_alarm_for_earlier_today_must_display_error(self):
        earlier_today = ...
        test_alarm_name = 'Test alarm for earlier_today'
        error_dialog = self.alarm_page.add_alarm_with_error(
            test_alarm_name, earlier_today)

        self.assertEqual(
            error_dialog.text,
            'Please select a time in the future.')

Take a look at the methods add\_alarm and add\_alarm\_with\_error. The
first one returns the Alarm page again, where the user can continue his
journey or finish the test checking the result. The second one returns
the error dialog that's expected when you try to add an alarm with the
wrong values.


[1] Meszaros, G. (2007). xUnit test patterns: Refactoring test code.
Pearson Education.

[2] Selenium community (2013, March 31). Page Objects. Retrieved from
https://code.google.com/p/selenium/wiki/PageObjects

Test Length
+++++++++++

Tests should be short - as short as possible while maintaining readability. Longer tests are harder to read, harder to understand, and harder to debug. Long tests are often symptomatic of several possible problems:

 * Your test requires complicated setup that should be encapsulated in a method or function.
 * Your test is actually several tests all jammed into one large test.

**Bad Example:**

.. code-block:: python

    def test_panel_title_switching_active_window(self):
        """Tests the title shown in the panel with a maximized application."""
        # Locked Launchers on all monitors
        self.set_unity_option('num_launchers', 0)
        self.set_unity_option('launcher_hide_mode', 0)

        text_win = self.open_new_application_window("Text Editor", maximized=True)

        self.assertTrue(text_win.is_maximized)
        self.assertThat(self.panel.title, Equals(text_win.title))
        sleep(.25)

        calc_win = self.open_new_application_window("Calculator")
        self.assertThat(self.panel.title, Equals(calc_win.application.name))

        icon = self.launcher.model.get_icon_by_desktop_id(text_win.application.desktop_file)
        launcher = self.launcher.get_launcher_for_monitor(self.panel_monitor)
        launcher.click_launcher_icon(icon)

        self.assertTrue(text_win.is_focused)
        self.assertThat(self.panel.title, Equals(text_win.title))

This test can be simplified into the following:

.. code-block:: python

    def test_panel_title_switching_active_window(self):
        """Tests the title shown in the panel with a maximized application."""
        text_win = self.open_new_application_window("Text Editor", maximized=True)
        self.open_new_application_window("Calculator")

        icon = self.launcher.model.get_icon_by_desktop_id(text_win.application.desktop_file)
        launcher = self.launcher.get_launcher_for_monitor(self.panel_monitor)
        launcher.click_launcher_icon(icon)

        self.assertTrue(text_win.is_focused)
        self.assertThat(self.panel.title, Equals(text_win.title))

Here's what we changed:

 * Removed the ``set_unity_option`` lines, as they didn't affect the test results at all.
 * Removed assertions that were duplicated from other tests. For example, there's already an autopilot test that ensures that new applications have their title displayed on the panel.

With a bit of refactoring, this test could be even smaller (the launcher proxy classes could have a method to click an icon given a desktop id), but this is now perfectly readable and understandable within a few seconds of reading.

Good docstrings
+++++++++++++++

Test docstrings are used to communicate to other developers what the test is supposed to be testing. Test Docstrings must:

 1. Conform to `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_ and `PEP257 <http://www.python.org/dev/peps/pep-0257/>`_ guidelines.
 2. Avoid words like "should" in favor of stronger words like "must".
 3. Contain a one-line summary of the test.

Additionally, they should:
 1. Include the launchpad bug number (if applicable).

**Good Example:**

.. code-block:: python

    def test_launcher_switcher_next_keeps_shortcuts(self):
        """Launcher switcher next action must keep shortcuts after they've been shown."""

Within the context of the test case, the docstring is able to explain exactly what the test does, without any ambiguity. In contrast, here's a poorer example:

**Bad Example:**

.. code-block:: python

    def test_switcher_all_mode_shows_all_apps(self):
        """Test switcher 'show_all' mode shows apps from all workspaces."""

The docstring explains what the desired outcome is, but without how we're testing it. This style of sentence assumes test success, which is not what we want! A better version of this code might look like this:

.. code-block:: python

    def test_switcher_all_mode_shows_all_apps(self):
        """Switcher 'show all' mode must show apps from all workspaces."""

The difference between these two are subtle, but important.

Test Readability
++++++++++++++++

The most important attribute for a test is that it is correct - it must test what's it's supposed to test. The second most important attribute is that it is readable. Tests should be able to be examined by themselves by someone other than the test author without any undue hardship. There are several things you can do to improve test readability:

1. Don't abuse the ``setUp()`` method. It's tempting to put code that's common to every test in a class into the ``setUp`` method, but it leads to tests that are not readable by themselves. For example, this test uses the ``setUp`` method to start the launcher switcher, and ``tearDown`` to cancel it:

 **Bad Example:**

 .. code-block:: python

     def test_launcher_switcher_next(self):
        """Moving to the next launcher item while switcher is activated must work."""
        self.launcher_instance.switcher_next()
        self.assertThat(self.launcher.key_nav_selection, Eventually(GreaterThan(0)))

 This leads to a shorter test (which we've already said is a good thing), but the test itself is incomplete. Without scrolling up to the ``setUp`` and ``tearDown`` methods, it's hard to tell how the launcher switcher is started. The situation gets even worse when test classes derive from each other, since the code that starts the launcher switcher may not even be in the same class!

 A much better solution in this example is to initiate the switcher explicitly, and use ``addCleanup()`` to cancel it when the test ends, like this:

 **Good Example:**

 .. code-block:: python

     def test_launcher_switcher_next(self):
        """Moving to the next launcher item while switcher is activated must work."""
        self.launcher_instance.switcher_start()
        self.addCleanup(self.launcher_instance.switcher_cancel)

        self.launcher_instance.switcher_next()
        self.assertThat(self.launcher.key_nav_selection, Eventually(GreaterThan(0)))

 The code is longer, but it's still very readable. It also follows the setup/action/test convention discussed above.

 Appropriate uses of the ``setUp()`` method include:

 * Initialising test class member variables.
 * Setting unity options that are required for the test. For example, many of the switcher autopilot tests set a unity option to prevent the switcher going into details mode after a timeout. This isn't part of the test, but makes the test easier to write.
 * Setting unity log levels. The unity log is captured after each test. Some tests may adjust the verbosity of different parts of the Unity logging tree.

2. Put common setup code into well-named methods. If the "setup" phase of a test is more than a few lines long, it makes sense to put this code into it's own method. Pay particular attention to the name of the method you use. You need to make sure that the method name is explicit enough to keep the test readable. Here's an example of a test that doesn't do this:

 **Bad Example:**

 .. code-block:: python

    def test_showdesktop_hides_apps(self):
        """Show Desktop keyboard shortcut must hide applications."""
        self.start_app('Character Map', locale='C')
        self.start_app('Calculator', locale='C')
        self.start_app('Text Editor', locale='C')

        # show desktop, verify all windows are hidden:
        self.keybinding("window/show_desktop")
        self.addCleanup(self.keybinding, "window/show_desktop")

        open_wins = self.bamf.get_open_windows()
        for win in open_wins:
            self.assertTrue(win.is_hidden)

 In contrast, we can refactor the test to look a lot nicer:

 **Good Example:**

 .. code-block:: python

    def test_showdesktop_hides_apps(self):
        """Show Desktop keyboard shortcut must hide applications."""
        self.launch_test_apps()

        # show desktop, verify all windows are hidden:
        self.keybinding("window/show_desktop")
        self.addCleanup(self.keybinding, "window/show_desktop")

        open_wins = self.bamf.get_open_windows()
        for win in open_wins:
            self.assertTrue(win.is_hidden)

 The test is now shorter, and the ``launch_test_apps`` method can be re-used elsewhere. Importantly - even though I've hidden the implementation of the ``launch_test_apps`` method, the test still makes sense.

3. Hide complicated assertions behind custom ``assertXXX`` methods or custom matchers. If you find that you frequently need to use a complicated assertion pattern, it may make sense to either:

 * Write a custom matcher. As long as you follow the protocol laid down by the ``testtools.matchers.Matcher`` class, you can use a hand-written Matcher just like you would use an ordinary one. Matchers should be written in the ``autopilot.matchers`` module if they're likely to be reusable outside of a single test, or as local classes if they're specific to one test.

 * Write custom assertion methods. For example:

  .. code-block:: python

    def test_multi_key_copyright(self):
        """Pressing the sequences 'Multi_key' + 'c' + 'o' must produce '©'."""
        self.dash.reveal_application_lens()
        self.keyboard.press_and_release('Multi_key')
        self.keyboard.type("oc")
        self.assertSearchText("©")

  This test uses a custom method named ``assertSearchText`` that hides the complexity involved in getting the dash search text and comparing it to the given parameter.

Prefer ``wait_for`` and ``Eventually`` to ``sleep``
++++++++++++++++++++++++++++++++++++++++++++++++++++

Early autopilot tests relied on extensive use of the python ``sleep`` call to halt tests long enough for unity to change its state before the test continued. Previously, an autopilot test might have looked like this:

**Bad Example:**

.. code-block:: python

    def test_alt_f4_close_dash(self):
        """Dash must close on alt+F4."""
        self.dash.ensure_visible()
        sleep(2)
        self.keyboard.press_and_release("Alt+F4")
        sleep(2)
        self.assertThat(self.dash.visible, Equals(False))

This test uses two ``sleep`` calls. The first makes sure the dash has had time to open before the test continues, and the second makes sure that the dash has had time to respond to our key presses before we start testing things.

There are several issues with this approach:
 1. On slow machines (like a jenkins instance running on a virtual machine), we may not be sleeping long enough. This can lead to tests failing on jenkins that pass on developers machines.
 2. On fast machines, we may be sleeping too long. This won't cause the test to fail, but it does make running the test suite longer than it has to be.

There are two solutions to this problem:

In Tests
--------

Tests should use the ``Eventually`` matcher. This can be imported as follows:

.. code-block:: python

 from autopilot.matchers import Eventually

The ``Eventually`` matcher works on all attributes in a proxy class that derives from ``UnityIntrospectableObject`` (at the time of writing that is almost all the autopilot unity proxy classes).

The ``Eventually`` matcher takes a single argument, which is another testtools matcher instance. For example, the bad assertion from the example above could be rewritten like so:

.. code-block:: python

 self.assertThat(self.dash.visible, Eventually(Equals(False)))

Since we can use any testtools matcher, we can also write code like this:

.. code-block:: python

 self.assertThat(self.launcher.key_nav_selection, Eventually(GreaterThan(prev_icon)))

Note that you can pass any object that follows the testtools matcher protocol (so you can write your own matchers, if you like).

In Proxy Classes
----------------

Proxy classes are not test cases, and do not have access to the ``self.assertThat`` method. However, we want proxy class methods to block until unity has had time to process the commands given. For example, the ``ensure_visible`` method on the Dash controller should block until the dash really is visible.

To achieve this goal, all attributes on unity proxy classes have been patched with a ``wait_for`` method that takes a testtools matcher (just like ``Eventually`` - in fact, the ``Eventually`` matcher just calls wait_for under the hood). For example, previously the ``ensure_visible`` method on the Dash controller might have looked like this:

**Bad Example:**

.. code-block:: python

    def ensure_visible(self):
        """Ensures the dash is visible."""
        if not self.visible:
            self.toggle_reveal()
            sleep(2)

In this example we're assuming that two seconds is long enough for the dash to open. To use the ``wait_for`` feature, the code looks like this:

**Good Example:**

.. code-block:: python

    def ensure_visible(self):
        """Ensures the dash is visible."""
        if not self.visible:
            self.toggle_reveal()
            self.visible.wait_for(True)

Note that wait_for assumes you want to use the ``Equals`` matcher if you don't specify one. Here's another example where we're using it with a testtools matcher:

.. code-block:: python

    key_nav_selection.wait_for(NotEquals(old_selection))


Scenarios
+++++++++

Autopilot uses the ``python-testscenarios`` package to run a test multiple times in different scenarios. A good example of scenarios in use is the launcher keyboard navigation tests: each test is run once with the launcher hide mode set to 'always show launcher', and again with it set to 'autohide launcher'. This allows test authors to write their test once and have it execute in multiple environments.

In order to use test scenarios, the test author must create a list of scenarios and assign them to the test case's ``scenarios`` *class* attribute. The autopilot ibus test case classes use scenarios in a very simple fashion:

**Good Example:**

.. code-block:: python

    class IBusTestsPinyin(IBusTests):
        """Tests for the Pinyin(Chinese) input engine."""

        scenarios = [
            ('basic', {'input': 'abc1', 'result': u'\u963f\u5e03\u4ece'}),
            ('photo', {'input': 'zhaopian ', 'result': u'\u7167\u7247'}),
            ('internet', {'input': 'hulianwang ', 'result': u'\u4e92\u8054\u7f51'}),
            ('disk', {'input': 'cipan ', 'result': u'\u78c1\u76d8'}),
            ('disk_management', {'input': 'cipan guanli ', 'result': u'\u78c1\u76d8\u7ba1\u7406'}),
        ]

        def test_simple_input_dash(self):
            self.dash.ensure_visible()
            self.addCleanup(self.dash.ensure_hidden)
            self.activate_ibus(self.dash.searchbar)
            self.keyboard.type(self.input)
            self.deactivate_ibus(self.dash.searchbar)
            self.assertThat(self.dash.search_string, Eventually(Equals(self.result)))

This is a simplified version of the IBus tests. In this case, the ``test_simple_input_dash`` test will be called 5 times. Each time, the ``self.input`` and ``self.result`` attribute will be set to the values in the scenario list. The first part of the scenario tuple is the scenario name - this is appended to the test id, and can be whatever you want.

.. Important::
   It is important to notice that the test does not change its behavior depending on the scenario it is run under. Exactly the same steps are taken - the only difference in this case is what gets typed on the keyboard, and what result is expected.

Scenarios are applied before the test's ``setUp`` or ``tearDown`` methods are called, so it's safe (and indeed encouraged) to set up the test environment based on these attributes. For example, you may wish to set certain unity options for the duration of the test based on a scenario parameter.

Multiplying Scenarios
---------------------

Scenarios are very helpful, but only represent a single-dimension of parameters. For example, consider the launcher keyboard navigation tests. We may want several different scenarios to come into play:

 1. A scenario that controls whether the launcher is set to 'autohide' or 'always visible'.
 2. A scenario that controls which monitor the test is run on (in case we have multiple monitors configured).

We can generate two separate scenario lists to represent these two scenario axis, and then produce the dot-product of thw two lists like this:

.. code-block:: python

    from autopilot.tests import multiply_scenarios

    class LauncherKeynavTests(AutopilotTestCase):

        hide_mode_scenarios = [
            ('autohide', {'hide_mode': 1}),
            ('neverhide', {'hide_mode': 0}),
        ]

        monitor_scenarios = [
            ('monitor_0', {'launcher_monitor': 0}),
            ('monitor_1', {'launcher_monitor': 1}),
        ]

        scenarios = multiply_scenarios(hide_mode_scenarios, monitor_scenarios)

(please ignore the fact that we're assuming that we always have two monitors!)

In the test classes ``setUp`` method, we can then set the appropriate unity option and make sure we're using the correct launcher:

.. code-block:: python

    def setUp(self):
        self.set_unity_option('launcher_hide_mode', self.hide_mode)
        self.launcher_instance = self.launcher.get_launcher_for_monitor(self.launcher_monitor)

Which allows us to write tests that work automatically in all the scenarios:

.. code-block:: python

    def test_keynav_initiates(self):
        """Launcher must start keyboard navigation mode."""
        self.launcher.keynav_start()
        self.assertThat(self.launcher.kaynav_mode, Eventually(Equals(True)))

This works fine. So far we've not done anything to cause undue pain.... until we decide that we want to extend the scenarios with an additional axis:

.. code-block:: python

    from autopilot.tests import multiply_scenarios

    class LauncherKeynavTests(AutopilotTestCase):

        hide_mode_scenarios = [
            ('autohide', {'hide_mode': 1}),
            ('neverhide', {'hide_mode': 0}),
        ]

        monitor_scenarios = [
            ('monitor_0', {'launcher_monitor': 0}),
            ('monitor_1', {'launcher_monitor': 1}),
        ]

        launcher_monitor_scenarios = [
            ('launcher on all monitors', {'monitor_mode': 0}),
            ('launcher on primary monitor only', {'monitor_mode': 1}),
        ]

        scenarios = multiply_scenarios(hide_mode_scenarios, monitor_scenarios, launcher_monitor_scenarios)

Now we have a problem: Some of the generated scenarios won't make any sense. For example, one such scenario will be ``(autohide, monitor_1, launcher on primary monitor only)``. If monitor 0 is the primary monitor, this will leave us running launcher tests on a monitor that doesn't contain a launcher!

There are two ways to get around this problem, and they both lead to terrible tests:

 1. Detect these situations and skip the test. This is bad for several reasons - first, skipped tests should be viewed with the same level of suspicion as commented out code. Test skips should only be used in exceptional circumstances. A test skip in the test results is just as serious as a test failure.

 2. Detect the situation in the test, and run different code using an if statement. For example, we might decode to do this:

 .. code-block:: python

     def test_something(self):
         # ... setup code here ...
         if self.monitor_mode == 1 and self.launcher_monitor == 1:
             # test something else
         else:
             # test the original thing.

 As a general rule, tests shouldn't have assert statements inside an if statement unless there's a very good reason for doing so.

Scenarios can be useful, but we must be careful not to abuse them. It is far better to spend more time typing and end up with clear, readable tests than it is to end up with fewer, less readable tests. Like all code, tests are read far more often than they're written.

.. _object_ordering:

Do Not Depend on Object Ordering
++++++++++++++++++++++++++++++++

Calls such as :meth:`~autopilot.introspection.ProxyBase.select_many` return several objects at once. These objects are explicitly unordered, and test authors must take care not to make assumptions about their order.

**Bad Example:**

.. code-block:: python

    buttons = self.select_many('Button')
    save_button = buttons[0]
    print_button = buttons[1]

This code may work initially, but there's absolutely no guarantee that the order of objects won't change in the future. A better approach is to select the individual components you need:

**Good Example:**

.. code-block:: python

    save_button = self.select_single('Button', objectName='btnSave')
    print_button = self.select_single('Button', objectName='btnPrint')

This code will continue to work in the future.
