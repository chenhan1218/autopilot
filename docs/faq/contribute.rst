Contribute
##########################

.. contents::

Autopilot: Contributing
+++++++++++++++++++++++
Q. How can I contribute to autopilot?
=====================================
* Documentation: We can always use more documentation.
    * if you don't know how to submit a merge proposal on launchpad, you can write a `bug <https://bugs.launchpad.net/autopilot/+filebug>`_ with new documentation and someone will submit a merge proposal for you. They will give you credit for your documentation in the merge proposal.


* New Features: Check out our existing `Blueprints <https://blueprints.launchpad.net/autopilot>`_ or create some yourself... Then code!


* Test and Fix: No project is perfect, log some `bugs <https://bugs.launchpad.net/autopilot/+filebug>`_ or `fix some bugs <https://bugs.launchpad.net/autopilot>`_.

Q. Where can I get help / support?
==================================

The developers hang out in the #ubuntu-autopilot IRC channel on irc.freenode.net.

Q. How do I download the code?
==============================
Autopilot is using Launchpad and Bazaar for source code hosting. If you're new to Bazaar, or distributed version control in general, take a look at the `Bazaar mini-tutorial first. <http://doc.bazaar.canonical.com/bzr.dev/en/mini-tutorial/index.html>`_

Install bzr open a terminal and type::

    sudo apt-get install bzr

Download the code::

    bzr branch lp:autopilot

This will create an autopilot directory and place the latest code there. You can also view the autopilot code `on the web <https://launchpad.net/autopilot>`_


Q. How do I submit the code for a merge proposal?
=================================================
After making the desired changes to the code or documentation and making sure the tests still run type::

    bzr commit

Write a quick one line description of the bug that was fix or the documentation that was written.

Signup for a `launchpad account <https://help.launchpad.net/YourAccount/NewAccount>`_, if you don't have one. Then using your launchpad id type::

    bzr push lp:~<launchpad-id>/autopilot/<text about merge here>

    example:
    bzr push lp:~chris.gagnon/autopilot/bug-fix-lp234567

All new features should have unit and/or functional test to make sure someone doesn't remove or break your new code with a future commit.

Q. How do I list the tests for the autopilot source code?
=========================================================
From the directory containing the autopilot source code type::

    autopilot list autopilot.tests

Q. How do I run the tests for the autopilot source code?
========================================================
From the directory containing the autopilot source code type::

    autopilot run autopilot.tests

To run a single test::

    autopilot run autopilot.tests.unit.test_version_utility_fns.VersionFnTests.test_get_version_string_shows_source_version
