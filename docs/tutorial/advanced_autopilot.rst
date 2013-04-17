Advanced Autopilot Features
###########################

This document covers advanced features in autopilot.

Test Scenarios
==============

.. write about using test scenarios here.

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
