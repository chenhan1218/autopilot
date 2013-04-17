Porting Autopilot Tests
#######################

This document contains hints as to what is required to port a test suite from any version of autopilot to any newer version.

.. contents::

A note on Versions
==================

Autopilot releases are reasonably tightly coupled with Ubuntu releases. However, the autopilot authors maintain separate version numbers, with the aim of separating the autopilot release cadence from the Ubuntu platform release cadence.

Autopilot versions earlier than 1.2 were not publicly announced, and were only used within Canonical. For that reason, this document assumes that version 1.2 is the lowest version of autopilot present `"in the wild"`.

Porting to Autopilot v1.3.x
===========================

The 1.3 release included many API breaking changes. Earlier versions of autopilot made several assumptions about where tests would be run, that turned out not to be correct. Autopilot 1.3 brought several much-needed features, including:

* A system for building pluggable implementations for several core components. This system is used in several areas:

 * The input stack can now generate events using either the X11 client libraries, or the UInput kernel driver. This is necessary for devices that do not use X11.
 * The display stack can now report display information for systems that use both X11 and the mir display server.
 * The process stack can now report details regarding running processes & their windows on both Desktop, tablet, and phone platforms.

* A large code cleanup and reorganisation. In particular, lots of code that came from the Unity 3D codebase has been removed if it was deemed to not be useful to the majority of test authors. This code cleanup includes a flattening of the autopilot namespace. Previously, many useful classes lived under the ``autopilot.emulators`` namespace. These have now been moved into the ``autopilot`` namespace.


.. TODO - add specific instructions on how to port tests from the 'old and busted' autopilot to the 'new hotness'. Do this when we actually start the porting work ourselves.
