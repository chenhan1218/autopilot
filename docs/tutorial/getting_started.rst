Writing Your First Test
#######################

This document contains everything you need to know to write your first autopilot test. It covers writing several simple tests for a sample Qt5/Qml application. However, it's important to note that nothing in this tutorial is specific to Qt5/Qml, and will work equally well with any other kind of application.

The Setup Phase
===============

.. TODO: re-cover the setup phase in a sentence. Show the initial test file outline, with a setUp method.

Starting the Application
++++++++++++++++++++++++

.. TODO: document how to start the application. Cover the various ways of starting an application.

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

.. TODO: Discuss the issues with running tests & appliation in separate processes, and how the Eventually matcher helps us overcome these problems. Cover the various ways the matcher can be used.
