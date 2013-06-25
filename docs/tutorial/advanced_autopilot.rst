Advanced Autopilot Features
###########################

This document covers advanced features in autopilot.

.. _cleaning-up:

Cleaning Up
===========

It is vitally important that every test you run leaves the system in exactly the same state as it found it. This means that:

* Any files written to disk need to be removed.
* Any environment variables set during the test run need to be un-set.
* Any applications opened during the test run need to be closed again.
* Any :class:`~autopilot.input.Keyboard` keys pressed during the test need to be released again.

All of the methods on :class:`~autopilot.testcase.AutopilotTestCase` that alter the system state will automatically revert those changes at the end of the test. Similarly, the various input devices will release any buttons or keys that were pressed during the test. However, for all other changes, it is the responsibility of the test author to clean up those changes.

For example, a test might require that a file with certain content be written to disk at the start of the test. The test case might look something like this::

    class MyTests(AutopilotTestCase):

        def make_data_file(self):
            open('/tmp/datafile', 'w').write("Some data...")

        def test_application_opens_data_file(self):
            """Our application must be able to open a data file from disk."""
            self.make_data_file()
            # rest of the test code goes here

However this will leave the :file:`/tmp/datafile` on disk after the test has finished. To combat this, use the :meth:`addCleanup` method. The arguments to :meth:`addCleanup` are a callable, and then zero or more positional or keyword arguments. The Callable will be called with the positional and keyword arguments after the test has ended.

Cleanup actions are called in the reverse order in which they are added, and are called regardless of whether the test passed, failed, or raised an uncaught exception. To fix the above test, we might write something similar to::

    import os


    class MyTests(AutopilotTestCase):

        def make_data_file(self):
            open('/tmp/datafile', 'w').write("Some data...")
            self.addCleanup(os.remove, '/tmp/datafile')

        def test_application_opens_data_file(self):
            """Our application must be able to open a data file from disk."""
            self.make_data_file()
            # rest of the test code goes here

Note that by having the code to generate the ``/tmp/datafile`` file on disk in a separate method, the test itself can ignore the fact that these resources need to be cleaned up. This makes the tests cleaner and easier to read.

Test Scenarios
==============

Occasionally test authors will find themselves writing multiple tests that differ in one or two subtle ways. For example, imagine a hypothetical test case that tests a dictionary application. The author wants to test that certain words return no results. Without using test scenarios, there are two basic approaches to this problem. The first is to create many test cases, one for each specific scenario (*don't do this*)::

    class DictionaryResultsTests(AutopilotTestCase):

        def test_empty_string_returns_no_results(self):
            self.dictionary_app.enter_search_term("")
            self.assertThat(len(self.dictionary_app.results), Equals(0))

        def test_whitespace_string_returns_no_results(self):
            self.dictionary_app.enter_search_term(" \t ")
            self.assertThat(len(self.dictionary_app.results), Equals(0))

        def test_punctuation_string_returns_no_results(self):
            self.dictionary_app.enter_search_term(".-?<>{}[]")
            self.assertThat(len(self.dictionary_app.results), Equals(0))

        def test_garbage_string_returns_no_results(self):
            self.dictionary_app.enter_search_term("ljdzgfhdsgjfhdgjh")
            self.assertThat(len(self.dictionary_app.results), Equals(0))

The main problem here is that there's a lot of typing in order to change exactly one thing (and this hypothetical test is deliberately short, to ease clarity. Imagine a 100 line test case!). Another approach is to make the entire thing one large test (*don't do this either*)::

    class DictionaryResultsTests(AutopilotTestCase):

        def test_bad_strings_returns_no_results(self):
            bad_strings = ("",
                " \t ",
                ".-?<>{}[]",
                "ljdzgfhdsgjfhdgjh",
                )
            for input in bad_strings:
                self.dictionary_app.enter_search_term(input)
                self.assertThat(len(self.dictionary_app.results), Equals(0))


This approach makes it easier to add new input strings, but what happens when just one of the input strings stops working? It becomes very hard to find out which input string is broken, and the first string that breaks will prevent the rest of the test from running, since tests stop running when the first assertion fails.

The solution is to use test scenarios. A scenario is a class attribute that specifies one or more scenarios to run on each of the tests. This is best demonstrated with an example::

    class DictionaryResultsTests(AutopilotTestCase):

        scenarios = [
            ('empty string', {'input': ""}),
            ('whitespace', {'input': " \t "}),
            ('punctuation', {'input': ".-?<>{}[]"}),
            ('garbage', {'input': "ljdzgfhdsgjfhdgjh"}),
            ]

        def test_bad_strings_return_no_results(self):
            self.dictionary_app.enter_search_term(self.input)
            self.assertThat(len(self.dictionary_app.results), Equals(0))

Autopilot will run the ``test_bad_strings_return_no_results`` once for each scenario. On each test, the values from the scenario dictionary will be mapped to attributes of the test case class. In this example, that means that the 'input' dictionary item will be mapped to ``self.input``. Using scenarios has several benefits over either of the other strategies outlined above:

* Tests that use strategies will appear as separate tests in the test output. The test id will be the normal test id, followed by the strategy name in parenthesis. So in the example above, the list of test ids will be::

   DictionaryResultsTests.test_bad_strings_return_no_results(empty string)
   DictionaryResultsTests.test_bad_strings_return_no_results(whitespace)
   DictionaryResultsTests.test_bad_strings_return_no_results(punctuation)
   DictionaryResultsTests.test_bad_strings_return_no_results(garbage)

* Since scenarios are treated as separate tests, it's easier to debug which scenario has broken, and re-run just that one scenario.

* Scenarios get applied before the ``setUp`` method, which means you can use scenario values in the ``setUp`` and ``tearDown`` methods. This makes them more flexible than either of the approaches listed above.

.. TODO: document the use of the multiply_scenarios feature.

Test Logging
============

.. Write about how tests can write things to the log.

Environment Patching
====================

.. Document TestCase.patch_environment and it's uses.

Custom Assertions
=================

.. Document the custom assertion methods present in AutopilotTestCase

Platform Selection
==================

.. Document the methods we have to get information about the platform we're running on, and how we can skip tests based on this information.

Gestures and Multitouch
=======================

.. How do we do multi-touch & gestures?

.. _tut-picking-backends:

Advanced Backend Picking
========================

Several features in autopilot are provided by more than one backend. For example, the :mod:`autopilot.input` module contains the :class:`~autopilot.input.Keyboard`, :class:`~autopilot.input.Mouse` and :class:`~autopilot.input.Touch` classes, each of which can use more than one implementation depending on the platform the tests are being run on.

For example, when running autopilot on a traditional ubuntu desktop platform, :class:`~autopilot.input.Keyboard` input events are probably created using the X11 client libraries. On a phone platform, X11 is not present, so autopilot will instead choose to generate events using the kernel UInput device driver instead.

Other autopilot systems that make use of multiple backends include the :mod:`autopilot.display` and :mod:`autopilot.process` modules. Every class in these modules follows the same construction pattern:

Default Creation
++++++++++++++++

By default, calling the ``create()`` method with no arguments will return an instance of the class that is appropriate to the current platform. For example::
    >>> from autopilot.input import Keyboard
    >>> kbd = Keyboard.create()

The code snippet above will create an instance of the Keyboard class that uses X11 on Desktop systems, and UInput on other systems. On the rare occaison when test authors need to construct these objects themselves, we expect that the default creation pattern to be used.

Picking a Backend
+++++++++++++++++

Test authors may sometimes want to pick a specific backend. The possible backends are documented in the API documentation for each class. For example, the documentation for the :meth:`autopilot.input.Keyboard.create` method says there are two backends available: the ``X11`` backend, and the ``UInput`` backend. These backends can be specified in the create method. For example, to specify that you want a Keyboard that uses X11 to generate it's input events::

    >>> from autopilot.input import Keyboard
    >>> kbd = Keyboard.create("X11")

Similarly, to specify that a UInput keyboard should be created::

    >>> from autopilot.input import Keyboard
    >>> kbd = Keyboard.create("UInput")

.. warning:: Care must be taken when specifying specific backends. There is no guarantee that the backend you ask for is going to be available across all platforms. For that reason, using the default creation method is encouraged.

Possible Errors when Creating Backends
++++++++++++++++++++++++++++++++++++++

Lots of things can go wrong when creating backends with the ``create`` method.

If autopilot is unable to create any backends for your current platform, a :exc:`RuntimeError` exception will be raised. It's ``message`` attribute will contain the error message from each backend that autopilot tried to create.

If a preferred backend was specified, but that backend doesn't exist (probably the test author mis-spelled it), a :exc:`RuntimeError` will be raised::

    >>> from autopilot.input import Keyboard
    >>> try:
    ...     kbd = Keyboard.create("uinput")
    ... except RuntimeError as e:
    ...     print "Unable to create keyboard:", e
    ...
    Unable to create keyboard: Unknown backend 'uinput'

In this example, ``uinput`` was mis-spelled (backend names are case sensitive). Specifying the correct backend name works as expected::

    >>> from autopilot.input import Keyboard
    >>> kbd = Keyboard.create("UInput")

Finally, if the test author specifies a preferred backend, but that backend could not be created, a :exc:`autopilot.BackendException` will be raised. This is an important distinction to understand: While calling ``create()`` with no arguments will try more than one backend, specifying a backend to create will only try and create that one backend type. The BackendException instance will contain the original exception raised by the backed in it's ``original_exception`` attribute. In this example, we try and create a UInput keyboard, which fails because we don't have the correct permissions (this is something that autopilot usually handles for you)::

    >>> from autopilot.input import Keyboard
    >>> from autopilot import BackendException
    >>> try:
    ...     kbd = Keyboard.create("UInput")
    ... except BackendException as e:
    ...     repr(e.original_exception)
    ...     repr(e)
    ...
    'UInputError(\'"/dev/uinput" cannot be opened for writing\',)'
    'BackendException(\'Error while initialising backend. Original exception was: "/dev/uinput" cannot be opened for writing\',)'



Process Control
===============

.. Document the process stack.

Display Information
===================

.. Document the display stack.

.. _custom_emulators:

Writing Custom Emulators
========================

By default, autopilot will generate an object for every introspectable item in your application under test. These are generated on the fly, and derive from
:class:`~autopilot.introspection.DBusIntrospectionObject`. This gives you the usual methods of selecting other nodes in the object tree, as well the the means to inspect all the properties in that class.

However, sometimes you want to customize the class used to create these objects. The most common reason to want to do this is to provide methods that make it easier to inspect these objects. Autopilot allows test authors to provide their own custom classes, through a couple of simple steps:

1. First, you must define your own base class, to be used by all emulators in your test suite. This base class can be empty, but must derive from :class:`~autopilot.introspection.CustomEmulatorBase`. An example class might look like this::

    from autopilot.introspection import CustomEmulatorBase


    class EmulatorBase(CustomEmulatorBase):
        """A base class for all emulators within this test suite."""

2. Define the classes you want autopilot to use, instead of the default. The class name must be the same as the type you wish to override. For example, if you want to define your own custom class to be used every time autopilot generates an instance of a 'QLabel' object, the class definition would look like this::

    class QLabel(EmulatorBase):

        # Add custom methods here...

3. As long as this custom class has been seen by the python interpreter (usually by importing it somewhere within the test suite), autopilot will use it every time it needs to generate a ``QLabel`` instance. You can also pass this class to methods like :meth:`~autopilot.introspection.DBusIntrospectionObject.select_single` instead of a string. So, for example, the following is a valid way of selecting the QLabel instances in an application::

    # self.app is the application proxy object.
    # Get all QLabels in the applicaton:
    labels = self.app.select_many(QLabel)
