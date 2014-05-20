===============
Troubleshooting
===============

.. contents::

-------------
Failing Tests
-------------

.. _failing_tests:

Q. Why is my test failing? It works some of the time. What cause "flakyness?"
=============================================================================

Sometimes a tests fails because the application under tests has issues, but what happens when the failing test can't be reproduced manually? It means the test itself has an issue.

Here is a troubleshooting guide you can use with some of the common problems that a developers can overlook while writing tests.

StateNotFoundError
==================

.. _state_not_found:

#. Not waiting for an animation to finish before looking for an object. Did you add animations to your app recently?

         * problem::

            self.main_view.select_single('Button', text='click_this')

         * solution::

            page.animationRunning.wait_for(False) 
            self.main_view.select_single('Button', text='click_this')

#. Not waiting for an object to become visible before trying to select it. Is your app slower than it used to be for some reason? Does it's properties have null values? Do you see errors in stdout while using your app, if you run it from the commandline?
         * problem::

            self.main_view.select_single('QPushButton', objectName='clickme')

         * solution::

            self.main_view.wait_select_single('QPushButton', objectName='clickme')

#. Waiting for a item that is destroyed to be not visible, sometimes the objects is destroyed before it returns false:
        * problem::

            self.assertThat(dialogButton.visible, Eventually(Equals(False)))

        * problem::

            self._get_activity_indicator().running.wait_for(False)


        * solution::

            dialogButton.wait_for_destroyed()

        * solution::

            self._get_activity_indicator().running.wait_for_destroyed()

#. Trying to use select_many like a list. Select_many is unordered, it will not return the same object every time.
        * problem::

            def get_first_photo(self):
                """Returns first photo"""
                return event.select_many('OrganicItemInteraction',
                                         objectName='eventsViewPhoto')[0]

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
