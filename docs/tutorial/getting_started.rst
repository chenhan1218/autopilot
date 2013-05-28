Writing Your First Test
#######################

This document contains everything you need to know to write your first autopilot test. It covers writing several simple tests for a sample Qt5/Qml application. However, it's important to note that nothing in this tutorial is specific to Qt5/Qml, and will work equally well with any other kind of application.

Files and Directories
=====================

Your autopilot test suite will grow to several files, possibly spread across several directories. We recommend that you follow this simple directory layout::

	autopilot/
	autopilot/<projectname>/
	autopilot/<projectname>/emulators/
	autopilot/<projectname>/tests/

The ``autopilot`` folder can be anywhere within your project's source tree. It will likely contain a `setup.py <http://docs.python.org/2/distutils/setupscript.html>`_ file.

The ``autopilot/<projectname>/`` folder is the base package for your autopilot tests. This folder, and all child folders, are python packages, and so must contain an `__init__.py file <http://docs.python.org/2/tutorial/modules.html#packages>`_.

The ``autopilot/<projectname>/emulators/``  directory is optional, and will only be used if you write custom emulators. This is an advanced topic, and is covered in a later section.

.. TODO: Link to the later section once we've written it.

Each test file should be named ``test_<component>.py``, where *<component>* is the logical component you are testing in that file. Test files must be written in the ``autopilot/<projectname>/tests/`` folder.

A Minimal Test Case
+++++++++++++++++++

Autopilot tests follow a similar pattern to other python test libraries: you must declare a class that derives from :class:`~autopilot.testcase.AutopilotTestCase`. A minimal test case looks like this::

	from autopilot.testcase import AutopilotTestCase


	class MyTests(AutopilotTestCase):

		def test_something(self):
			"""An example test case that will always pass."""
			self.assertTrue(True)

.. otto:: **Make your tests expressive!**

	It's important to make sure that your tests express your *intent* as clearly as possible. We recommend choosing long, descriptive names for test functions and classes (even breaking PEP8, if you need to), and give your tests a detailed docstring explaining exactly what you are trying to test. For more detailed advice on this point, see :ref:`write-expressive-tests`

The Setup Phase
===============

Before each test is run, the ``setUp`` method is called. Test authors may override this method to run any setup that needs to happen before the test is run. However, care must be taken when using the ``setUp`` method: it tends to hide code from the test case, which can make your tests less readable. It is our recommendation, therefore, that you use this feature sparingly. A more suitable alternative is often to put the setup code in a separate function or method and call it from the test function.

Should you wish to put code in a setup method, it looks like this:

.. code-block:: python

	from autopilot.testcase import AutopilotTestCase


	class MyTests(AutopilotTestCase):

		def setUp(self):
			super(MyTests, self).setUp()
			# This code gets run before every test!

		def test_something(self):
			"""An example test case that will always pass."""
			self.assertTrue(True)

.. note::
	Any action you take in the setup phase must be undone if it alters the system state. See :ref:`cleaning-up` for more details.

Starting the Application
++++++++++++++++++++++++

At the start of your test, you need to tell autopilot to launch your application. To do this, call :meth:`~autopilot.testcase.AutopilotTestCase.launch_test_application`. The minimum required argument to this method is the application name or path. If you pass in the application name, autopilot will look in the current working directory, and then will search the :envvar:`PATH` environment variable. Otherwise, autopilot looks for the executable at the path specified. Positional arguments to this method are passed to the executable being launched.

Autopilot will try and guess what type of application you are launching, and therefore what kind of introspection libraries it should load. Sometimes autopilot will need some assistance however. For example, at the time of writing, autopilot cannot automatically detect the introspection type for python / Qt4 applications. In that case, a :class:`RuntimeError` will be raised. To provide autopilot with a hint as to which introspection type to load, you can provide the ``app_type`` keyword argument. For example::

	class MyTests(AutopilotTestCase):

		def test_python_qt4_application(self):
			self.app = self.launch_test_application(
				'my-pyqt4-app',
				app_type='qt'
				)

See the documentation for :meth:`~autopilot.testcase.AutopilotTestCase.launch_test_application` for more details.

What is a Proxy Object?
=======================

.. TODO: Cover what the return of start_test_application is, and how it works. Draw a pretty diagram thing :)

A Simple Test
=============

.. TODO: Write an initial test - something simple - perhaps read the application window title bar. Discuss the basics of how introspection works.

Running Autopilot
+++++++++++++++++

.. TODO: A quick example of how to run this test, with a link to the larger and more complete section on using the autopilot command line utility.

A Test with Interaction
=======================

.. TODO: Add a second test, one that adds some keyboard / mouse interaction.

The Eventually Matcher
======================

.. TODO: Discuss the issues with running tests & application in separate processes, and how the Eventually matcher helps us overcome these problems. Cover the various ways the matcher can be used.
