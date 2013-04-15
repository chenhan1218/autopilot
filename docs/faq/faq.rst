:orphan:

Frequently Asked Questions
##########################

.. contents::

Autopilot: The Project
++++++++++++++++++++++

Q. How do I install Autopilot?
==============================

The easiest way is by running Ubuntu Raring, and typing::

    sudo apt-get install python-autopilot

in a terminal. This will download and install the latest autopilot release, along with the documentation. If you're not running Ubuntu Raring, you can download the source code from the `autopilot project page <http://launchpad.net/autopilot/>`_.

Q. Where can I report a bug?
============================

Autopilot is hosted on launchpad - bugs can be reported on the `launchpad bug page for autopilot <https://bugs.launchpad.net/autopilot/+filebug>`_ (this requires a launchpad account).

Q. Where can I get help / support?
==================================

The developers hang out in the #ubuntu-quality IRC channel on irc.freenode.net.

Q. What type of applications can autopilot test?
================================================

Autopilot works with severall different types of applications, including:
 * The Unity desktop shell.
 * Gtk 2 & 3 applications.
 * Qt4, Qt5, and Qml applications.

Autopilot is designed to work across all the form factors Ubuntu runs on, including the phone and tablet.

Autopilot Tests
+++++++++++++++

.. _faq-many-asserts:

Q. Autopilot tests often include multiple assertions. Isn't this bad practise?
==============================================================================

Maybe. But probably not.

Unit tests should test a single unit of code, and ideally be written such that they can fail in exactly a single way. Therefore, unit tests should have a single assertion that determines whether the test passes or fails.

However, autopilot tests are not unit tests, they are functional tests. Functional test suites tests features, not units of code, so there's several very good reasons to have more than assertion in a single test:

* Some features require several assertions to prove that the feature is working correctly. For example, you may wish to verify that the 'Save' dialog box opens correctly, using the following code::

    self.assertThat(save_win.title, Eventually(Equals("Save Document")))
    self.assertThat(save_win.visible, Equals(True))
    self.assertThat(save_win.has_focus, Equals(True))

* Some tests need to wait for the application to respond to user input before the test continues. The easiest way to do this is to use the :class:`~autopilot.matchers.Eventually` matcher in the middle of your interaction with the application. For example, if testing the `Firefox <http://www.mozilla.org/en-US/>`_ browsers ability to print a certain web comic, we might produce a test that looks similar to this::

    def test_firefox_can_print_xkcd(self):
        """Firefox must be able to print xkcd.com."""
        # Put keyboard focus in URL bar:
        self.keyboard.press_and_release('Ctrl+l')
        self.keyboard.type('http://xkcd.com')
        self.keyboard.press_and_release('Enter')
        # wait for page to load:
        self.assertThat(self.app.loading, Eventually(Equals(False)))
        # open print dialog:
        self.keyboard.press_and_release('Ctrl+p')
        # wait for dialog to open:
        self.assertThat(self.app.print_dialog.open, Eventually(Equals(True)))
        self.keyboard.press_and_release('Enter')
        # ensure something was sent to our faked printer:
        self.assertThat(self.fake_printer.documents_printed, Equals(1))

In general, autopilot tests are more relaxed about the 'one assertion per test' rule. However, care should still be taken to produce tests that are as small and understandable as possible.

Autopilot Qt & Gtk Support
++++++++++++++++++++++++++

Q. What is the impact on memory of adding objectNames to QML items?
===================================================================

The objectName is a QString property of QObject which defaults to an empty QString.
QString is UTF-16 representation and because it uses some general purpose
optimisations it usually allocates twice the space it needs to be able to grow
fast. It also uses implicit sharing with copy-on-write and other similar
tricks to increase performance again. These properties makes the used memory
not straightforward to predict. For example, copying an object with an
objectName, shares the memory between both as long as they are not changed.

When measuring memory consumption, things like memory alignment come into play.
Due to the fact that QML is interpreted by a JavaScript engine, we are working
in levels where lots of abstraction layers are in between the code and the
hardware and we have no chance to exactly measure consumption of a single
objectName property. Therefore the taken approach is to measure lots of items
and calculate the average consumption.

.. table:: Measurement of memory consumption of 10000 Items

    ================== ====================== ====================
    Without objectName With unique objectName With same objectName
    ================== ====================== ====================
    65292 kB           66628 kB               66480 kB
    ================== ====================== ====================

=> With 10000 different objectNames 1336 kB of memory are consumed which is
around 127 Bytes per Item.

Indeed, this is more than only the string. Some of the memory is certainly lost
due to memory alignment where certain areas are just not perfectly filled in
but left empty. However, certainly not all of the overhead can be blamed on
that. Additional memory is used by the QObject meta object information that is
needed to do signal/slot connections. Also, QML does some optimisations: It
does not connect signals/slots when not needed. So the fact that the object
name is set could trigger some more connections.

Even if more than the actual string size is used and QString uses a large
representation, this is very little compared to the rest. A qmlscene with just
the item is 27MB. One full screen image in the Nexus 10 tablet can easily
consume around 30MB of memory. So objectNames are definitely not the first
places where to search for optimisations.

Writing the test code snippets, one interesting thing came up frequently: Just
modifying the code around to set the objectName often influences the results
more than the actual string. For example, having a javascript function that
assigns the objectName definitely uses much more memory than the objectName
itself. Unless it makes sense from a performance point of view (frequently
changing bindings can be slow), objectNames should be added by directly
binding the value to the property instead using helper code to assign it.

Conclusion: If an objectName is needed for testing, this is definitely worth
it. objectName's should obviously not be added when not needed. When adding
them, the `general QML guidelines for performance should be followed. <http://qt-project.org/doc/qt-5.0/qtquick/qtquick-performance.html>`_
