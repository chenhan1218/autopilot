What is Autopilot, and what can it do?
######################################


Autopilot is a tool for writing functional tests. Functional tests are tests that:

* Run out-of-process. I.e.- the tests run in a separate process to the application under test.
* Simulate user interaction. Autopilot provides methods to generate keyboard, mouse, and touch events. These events are delivered to the application under test in exactly the same way as normal input events. The application under test therefore cannot distinguish between a "real" user and an autopilot test case.
* Validate design decisions. The primary function of a functional test is to determine whether of not an application has met the design criteria. Functional tests evaluate high-level design corectness.

.. image:: /images/test_pyramid.*

Autopilot exists at the apex of the "testing pyramid". It is designed to test high-level functionality, and complement a solid base of unit and integration tests.

A typical autopilot test has three distinct stages:

.. image:: /images/test_stages.*

**The Setup Stage**

There are several concerns that must be addressed in the setup Phase. The most important step is to launch the application to be tested. Most autopilot test suites launch the application under test anew for each test. This ensures that the test starts with the application under test in a known, clean state.

Tests may also wish to take other actions in the setup stage, including:

* Setting environment variables to certain values.
* Starting external applications that are required for the test to run.
* Creating files or folders (or any kind of external data) on disk.
