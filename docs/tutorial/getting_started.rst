Getting Started
+++++++++++++++

Autopilot is a tool for *functional* testing an application. The basic idea is
that we simulate user input at a very low level, and verify that the application
under test responds the way we expect it to. Autopilot provides two main
facilities to make this possible:


1. **Input Device Emulation**. Autopilot provides several classes that are able
to generate input device events. Keyboard and Mouse events are trivial to
generate, and other devices may be added in the future. See for example the
:class:`Keyboard <autopilot.emulators.X11.Keyboard>` and :class:`Mouse
<autopilot.emulators.X11.Mouse>` classes.

2. **State Introspection**. Autopilot provides several methods of inspecting
the applications state, and using the results of that introspection in a test.

Autopilot builds on top of several python unity testing tools. In particular,
autopilot tests are written in much the same manner as a python unit test would
be.

Autopilot tests are based on classic python unit tests. Specifically, autopilot
is built on top of the `python-testtools` module. Autopilot tests also
frequently make use of the `python-testscenarios` package, so familiarity with
this will help you understand existing test suites.

Autopilot Targets
=================

Autopilot allows you to write tests for several different targets, including:

* The Unity desktop shell. This was the original target for the autopiolot
  tool, and as such contains the most comprehensive test suite.

* Qt 4.x applications. Autopilot can introspect Qt 4.x applications with the
  help of the autopilot-qt package.

* Qt 5.x applications. Autopilot can introspect these applications with the
  help of the autopilot-qt5 package.

* Gtk 3.x applications. Autopilot can introspect Gtk applications with the
  help of the autopilot-gtk package.

The details of how to write an autopilot tests is remarkably similar across
these different targets. The only thing that changes is the way in which the
application under test is started.

When testing the unity desktop shell, Unity must be started before the
autopilot test is run. There are no special steps that must be taken in order
to enable autopilot introspection within Unity - it is enabled by default.

For applications, however, the application under test must be started from
within the autopilot test.

Starting a Qt application
-------------------------

Test suites for Qt applications must derive from both the
:class:`~autopilot.testcase.AutopilotTestCase` class and
the :class:`~autopilot.introspection.qt.QtIntrospectionTestMixin` class. The application under test can then be started by calling the
:meth:`launch_test_application(application)` method, like so::

    class MyFirstQtTests(AutopilotTestCase, QtIntrospectionTestMixin):

        def setUp(self):
            super(MyFirstQtTests, self).setUp()
            self.application = self.launch_test_application('myappname')

Note that the :meth:`launch_test_application(application)` accepts several different options, including:

* The name of the executable file, without a path component. In this case, the executable will be searched for in $PATH.
* The name of the executable file, with a path component.
* A .desktop file, either with, or without a path component.

Starting a Qt/Qml application
-----------------------------

There are two different approaches to running a Qml application under autopilot - either compile the Qml appalication into a binary that can be run as described above, or run the Qml file within qmlview, like so::

    class MyFirstQtTests(AutopilotTestCase, QtIntrospectionTestMixin):

        def setUp(self):
            super(MyFirstQtTests, self).setUp()
            self.application = self.launch_test_application('qmlviewer', 'myfule.qml')

Starting a Gtk application
--------------------------

Gtk applications are started in a similar manner to Qt applications. The test case class must derive from :class:`~autopilot.introspection.gtk.GtkIntrospectionTestMixin`. Simply call :meth:`launch_test_application(application)` with the application path::

    class MyFirstGtkTests(AutopilotTestCase, GtkIntrospectionTestMixin):

        def setUp(self):
            super(MyFirstQtTests, self).setUp()
            self.application = self.launch_test_application('myappname')

Test Basics
===========

Autopilot tests typically have three distinct stages:

1. **Test Setup.** Do whatever it takes to get to the point where the thing you're trying to test is ready. This typically involves launching the application under test (not applicable to the Unity shell, as discussed above) and navigating to the component that you want to test.

2. **Test Actions.** Send input events to the applicatio under test to mimic a user interaction. This typically involves using the :class:`~autopilot.emulators.X11.Keyboard` or :class:`~autopilot.emulators.X11.Mouse` classes.

3. **Test Assertions.** Do one or more test assertions to verify that the application under test performed as expected.

We will examine these three stages in detail.

Test Setup
----------

Setup actions generally fall into one of two categories:

If the setup action needs to be performed in exactly the same way for every test in the test case, the setup action can be placed inside the setUp method of the test case class. On the other hand, if the setup action is specific to one test, it should be placed at the beginning of the test in question.

Undoing Setup
#############

Make sure that where applicable, any action performed during a test that affects the system is undone at the end of the test. The recommended way of doing this is to call :meth:`~autopilot.testcase.AutopilotTestCase.addCleanup`, passing in a callable and (optionally) arguments that undo the specific action. For example, a test may need to write files to disk during the test setup phase, and clear them up again afterwards. This might be written like so::

    from os import remove
    from tempfile import mktemp


    class CleanupExamplTests(AutopilotTestCase):

        def test_something(self):
            file_path = mktemp()
            open(file_path, 'w').write("Hello World")
            self.addCleanup(remove, file_path)

            # test code goes here - 'file_path' will be removed at test end.

The addCleanup method can be used anywhere in the test code, including the setUp method. Using addCleanup is recommended over using the tearDown method.

You may use addCleanup as many times as you want - they will be run in the reverse order in which they were added. If a cleanup action raises an exception, the exception will be caught, and the test will error, but all remaining cleanup actions will still be run.

Test Actions
------------

Test actions will almost always involve simulating user interaction with the application under test. The two principle means of achieving this are generating Keyboard and Mouse events.

Using the Keyboard
##################

All classes that derive from :class:`~autopilot.testcase.AutopilotTestCase` have a 'keyboard' attribute that is an instance of :class:`~autopilot.emulators.X11.Keyboard`. We recommend that test authors use this instance of the Keyboard class instead of creating new instances. The :class:`~autopilot.emulators.X11.Keyboard` class has several capabilities:

* **Typing Text**. The most common operation is typing text. This can be achieved by calling the 'type' method, like so::

    self.keyboaqrd.type("Hello World")

  Here, each character in the string passed in he pressed and released in sequence. If all goes well, the application under test will recieve the characters 'H', 'e', 'l', 'l', 'o', ' ', 'W', 'o', 'r', 'l', 'd' - in that order.

* **Key Combinations**. Often a test needs to simulate a user pressing a key combination, like 'Ctrl+a'. This is achieved like this::

    self.keyboard.press_and_release('Ctrl+a')

  Here, each key is represented with a code separated by a '+' character. Key names follow the standard set in the X11 headers. All the keys mentioned in the string are pressed, and then all the keys are released. Key release events are generated in the reverse order than they are pressed, so the example above generated the following events:

  1. Press Ctrl
  2. Press a
  3. release a
  4. release Ctrl

* The keyboard class also contains 'press' and 'release' methods. These take the same parameters as the press_and_release method.

The Keybindings System
~~~~~~~~~~~~~~~~~~~~~~

Autopilot includes the :module:`autopilot.keybindings` module, which includes code to make it easier to send pre-configured keybindings to the application under test. The difficulty with keybindings is that most applications allow the user to configure the keybindings at will. If a user has changed the default keybindings, your autopilot tests will break if you have the default keys hard-coded in your tests. To overcome this, the keybindings system allows you to name a keybinding, and autopilot will read the actual keys to press and release from the application under test.

.. note:: At the time of writing, the keybindings system only works when teting Unity. Work is in progress to make this feature work with Qt and Gtk targets.

To use the keybindings system, you need to derive from the :class:`~autopilot.keybindings.KeybindingsHelper` class. This class adds the :meth:`~autopilot.keybindings.KeybindingsHelper.keybinding(binding_name, delay)` method, which allows you to send keybindings, like so::

    from autopilot.testcase import AutopilotTestCase
    from autopilot.keybindings import KeybindingsHelper


    class DashRevealTest(AutopilotTestCase, KeybindingsHelper):

        def test_dash_reveals_with_keybindings(self):
            self.keybinding("dash/reveal")
            self.addCleanup(self.dash.ensure_hidden)

            self.assertThat(dash.visible, Eventually(Equals(True)))

Using the Mouse
###############

All classes that derive from :class:`~autopilot.testcase.AutopilotTestCase` have a 'mouse' attribute that is an instance of :class:`~autopilot.emulators.X11.Mouse`. We recommend that test authors use this instance of the Mouse class instead of creating new instances. The :class:`~autopilot.emulators.X11.Mouse` class has several capabilities:

* **Querying mouse pointer location**. The Mouse class contains two attributes that give the x and y position of the mouse. These can be used to work out where the mouse is::

    class MouseQueryTests(AutopilotTestCase):

        def test_mouse_position(self):
            print "Mouse is at %d, %d." % (self.mouse.x, self.mouse.y)

* **Moving the Mouse**. There are two ways to move the mouse pointer, either by calling the 'move' method::

    self.mouse.move(123, 767)

  This will move the mouse to position (123, 767) on the screen. Often within a test you need to move the mouse to the position of an object that you already have (a button, perhaps). One (boring) way to achieve this is::

    self.mouyse.move( btn.x + btn.width / 2, btn.y + btn.height / 2)

  However, that's a lot of typing. There's a convenience method that works for most objects called 'move_to_object'. Use it like so::

    self.mouse.move_to_object(btn)

  This method does exactly what you'd expect it to do.

* **Clicking mouse buttons**. The most common action is to click the left mouse button once. This can be achieved simply::

    self.mouse.click()

  Clicking a button other than the left mouse button is easy too::

    self.mouse.click(button=2)

* **Mouse Drag & Drop**. Like the Keyboard class, the Mouse class has methods for pressing and releasing buttons, so a mouse drag might look like this::

    self.mouse.press()
    self.mouse.move(100,100)
    self.mouse.release()

Test Assertions
---------------

Autopilot is built on top of the standard python unit test tools - all the test assertion methods that are provided by the :module:`unittest` and :module:`testtools` modules are available to an autopilot test. However, autopilot adds a few additional test assertions that may be useful to test authors.

The authors of autopilot recommend that test authors make use of the :meth:`~testtools.TestCase.assertThat` method in their tests. The :module:`autopilot.matchers` module provides the :class:`~autopilot.matchers.Eventually` matcher, which introduces a timeout to the thing meing tested. This keep autopilot tests accurate, since the application under test is in a separate process, and event handling usually happens in an asynchronous fashion. As an example, here's a simple test that ensures that the unity dash is revealed when the 'Super' key is pressed::

    test_dash_is_revealed(self):
        dash = ... # Get the dash object from somewhere
        self.keyboard.press_and_release('Super')

        self.assertThat(dash.visible, Eventually(Equals(True)))

If we didn't use the Eventually matcher, this test might fail if the assertion method was executed before Unity had a chance to reveal the dash. The Eventually matcher is usable on any property that has been transmitted over DBus. The Eventually matcher will n ot work on calculated values, or values that have been obtained from some other source.

To do assertions with a similar timeout in places where Eventually does not work, the :class:`~autopilot.testcase.AutopilotTestCase` class includes the :meth:`~autopilot.testcase.AutopilotTestCase.assertProperty` method. This method takes an object, and a number of keyword arguments. These arguments will be applied to the object and tested, using a similar timeout mechanism to the Eventually matcher. For example, the above example could be re-written to use the assertProperty method::

    test_dash_is_revealed(self):
        dash = ... # Get the dash object from somewhere
        self.keyboard.press_and_release('Super')

        self.assertProperty(dash, visible=True)

One large drawback of the assertProperty method is that it can only test for equality, while other methods of assertion can test anything there is a testtools matcher class for.
