===============
Troubleshooting
===============

.. contents::

-------------
Failing Tests
-------------

.. _failing_tests:

Q. Why is my test failing? It works some of the time. What causes "flakyness?"
=============================================================================

Sometimes a tests fails because the application under tests has issues, but what happens when the failing test can't be reproduced manually? It means the test itself has an issue.

Here is a troubleshooting guide you can use with some of the common problems that developers can overlook while writing tests.

StateNotFoundError Exception
============================

.. _state_not_found:

1. Not waiting for an animation to finish before looking for an object. Did you add animations to your app recently?

         * problem::

            self.main_view.select_single('Button', text='click_this')

         * solution::

            page.animationRunning.wait_for(False) 
            self.main_view.select_single('Button', text='click_this')

2. Not waiting for an object to become visible before trying to select it. Is your app slower than it used to be for some reason? Does its properties have null values? Do you see errors in stdout/stderr while using your app, if you run it from the commandline?

 Python code is executed in series which takes milliseconds, whereas the actions (clicking a button etc.) will take longer as well as the dbus query time. This is why wait_select_* is useful i.e. click a button and wait for that click to happen (including the dbus query times taken).

         * problem::

            self.main_view.select_single('QPushButton', objectName='clickme')

         * solution::

            self.main_view.wait_select_single('QPushButton', objectName='clickme')

3. Waiting for an item that is destroyed to be not visible, sometimes the objects is destroyed before it returns false:
        * problem::

            self.assertThat(dialogButton.visible, Eventually(Equals(False)))

        * problem::

            self._get_activity_indicator().running.wait_for(False)


        * solution::

            dialogButton.wait_for_destroyed()

        * solution::

            self._get_activity_indicator().running.wait_for_destroyed()

4. Trying to use select_many like a list. The order in which the objects are returned are non-deterministic.
        * problem::

            def get_first_photo(self):
                """Returns first photo"""
                return event.select_many(
                    'OrganicItemInteraction',
                    objectName='eventsViewPhoto'
                )[0]

        * solution::

            def _get_named_photo_element(self, photo_name):
                """Return the ShapeItem container object for the named photo 
                This object can be clicked to enable the photo to be selected. 
                """
                photo_element = self.grid_view().wait_select_single(
                    'QQuickImage', source=photo_name)
                return photo_element.get_parent()

            def select_named_photo(self, photo_name):
                """Select the named photo from the picker view."""
                photo_element = self._get_named_photo_element(photo_name) 
                self.pointing_device.click_object(photo_element)
