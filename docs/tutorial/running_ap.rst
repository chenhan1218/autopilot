Running Autopilot
=================

Autopilot test suites can be run with any python test runner (for example, the built-in testtools runner). However, several autopilot features are only available if you use the autopilot runner.

List Tests
----------

Autopilot can list all tests found within a particular module::

    $ autopilot list <modulename>

where *<modulename>* is the base name of the module you want to look at. The module must either be in the current working directory, or be importable by python. For example, to list the tests inside autopilot itself, you can run::

     $ autopilot list autopilot
        autopilot.tests.test_ap_apps.GtkTests.test_can_launch_qt_app
        autopilot.tests.test_ap_apps.QtTests.test_can_launch_qt_app
        autopilot.tests.test_application_mixin.ApplicationSupportTests.test_can_create
        autopilot.tests.test_application_mixin.ApplicationSupportTests.test_launch_raises_ValueError_on_unknown_kwargs
        autopilot.tests.test_application_mixin.ApplicationSupportTests.test_launch_raises_ValueError_on_unknown_kwargs_with_known
        autopilot.tests.test_application_mixin.ApplicationSupportTests.test_launch_with_bad_types_raises_typeerror
        autopilot.tests.test_application_registration.ApplicationRegistrationTests.test_can_register_new_application
        autopilot.tests.test_application_registration.ApplicationRegistrationTests.test_can_unregister_application
        autopilot.tests.test_application_registration.ApplicationRegistrationTests.test_registering_app_twice_raises_KeyError
        autopilot.tests.test_application_registration.ApplicationRegistrationTests.test_unregistering_unknown_application_raises_KeyError
        ...

         81 total tests.

Some resuls have been omitted for clarity.

The list command takes only one option:

-ro, --run-order    Display tests in the order in which they will be run,
                    rather than alphabetical order (which is the default).

Run Tests
---------

Running autopilot tests is very similar to listing tests::

    $ autopilot run <modulename>

However, the run command has many more options to customise the run behavior:

-h, --help            show this help message and exit
-o OUTPUT, --output OUTPUT
                      Write test result report to file. Defaults to stdout.
                      If given a directory instead of a file will write to a
                      file in that directory named:
                      <hostname>_<dd.mm.yyy_HHMMSS>.log
-f FORMAT, --format FORMAT
                      Specify desired output format. Default is "text".
                      Other option is 'xml' to produce junit xml format.
-r, --record          Record failing tests. Required 'recordmydesktop' app
                      to be installed. Videos are stored in /tmp/autopilot.
-rd PATH, --record-directory PATH
                      Directory to put recorded tests (only if -r)
                      specified.
-v, --verbose         If set, autopilot will output test log data to stderr
                      during a test run.

Common use cases
++++++++++++++++

1. **Run autopilot and save the test log**::

    $ autopilot run -o . <modulename>

  Autopilot will create a text log file named <hostname>_<dd.mm.yyy_HHMMSS>.log with the contents of the test log.

2. **Run autopilot and record failing tests**::

    $ autopilot run -r --rd . <modulename>

  Videos are recorded as *ogg-vorbis* files, with an .ogv extension. They will be named with the test id that failed. All videos will be placed in the directory specified by the ``-rd`` option - in this case the currect directory. If this option is omitted, videos will be placed in ``/tmp/autopilot/``.

3. **Save the test log as jUnitXml format**::

    $ autopilot run -o results.xml -f xml <modulename>

  The file 'results.xml' will be created when all the tests have completed, and will be in the jUnitXml file format. This is useful when running the autopilot tests within a jenkins environment.

Visualise Introspection Tree
----------------------------

A very common thing to want to do while writing autopilot tests is see the structure of the application being tested. To support this, autopilot includes a simple application to help visualise the intropection tree. To start it, make sure the application you wish to test is running, and then run::

    $ autopilot vis

The result should be a window similar to below:

.. image:: /images/ap_vis_front_page.png

Selecting a connection from the drop-down box allows you to inspect different autopilot-supporting applications. If Unity is running, the Unity connection should always be present. If other applications have been started with the autopilot support enabled, they should appear in this list as well. Once a connection is selected, the introspection tree is rendered in the left-hand pane, and the details of each object appear in the right-hand pane.

.. image:: /images/ap_vis_object.png

