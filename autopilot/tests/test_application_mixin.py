# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.

from __future__ import absolute_import

from testtools import TestCase
from testtools.matchers import Equals, Is, Not, raises
from mock import patch

from autopilot.introspection.qt import QtIntrospectionTestMixin
from autopilot.testcase import AutopilotTestCase


def dummy_addCleanup(*args, **kwargs):
    pass

class ApplicationSupportTests(TestCase):

    def test_can_create(self):
        mixin = QtIntrospectionTestMixin()
        self.assertThat(mixin, Not(Is(None)))

    def test_launch_with_bad_types_raises_typeerror(self):
        """Calling launch_test_application with something other than a string must
        raise a TypeError"""

        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        self.assertThat(lambda: mixin.launch_test_application(1), raises(TypeError))
        self.assertThat(lambda: mixin.launch_test_application(True), raises(TypeError))
        self.assertThat(lambda: mixin.launch_test_application(1.0), raises(TypeError))
        self.assertThat(lambda: mixin.launch_test_application(object()), raises(TypeError))
        self.assertThat(lambda: mixin.launch_test_application(None), raises(TypeError))
        self.assertThat(lambda: mixin.launch_test_application([]), raises(TypeError))
        self.assertThat(lambda: mixin.launch_test_application((None,)), raises(TypeError))

    @patch('autopilot.introspection.qt.launch_application_from_desktop_file')
    def test_launch_can_classify_absolute_desktop_file(self, mock):
        """launch_test_application must be able to correctly classify an absolute
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        absolute_desktop_file = '/usr/share/applications/gedit.desktop'
        mixin.launch_test_application(absolute_desktop_file)

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((absolute_desktop_file,)))

    @patch('autopilot.introspection.qt.launch_application_from_desktop_file')
    def test_launch_can_classify_relative_desktop_file(self, mock):
        """launch_test_application must be able to correctly classify a relative
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        relative_desktop_file = 'gedit.desktop'
        mixin.launch_test_application(relative_desktop_file)

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((relative_desktop_file,)))

    @patch('autopilot.introspection.qt.launch_application_from_path')
    def test_launch_can_classify_absolute_app_path(self, mock):
        """launch_test_application must be able to correctly classify an absolute
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        absolute_path = '/usr/bin/gedit'
        mixin.launch_test_application(absolute_path)

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((absolute_path,)))

    @patch('autopilot.introspection.qt.launch_application_from_path')
    def test_launch_can_classify_relative_app_path(self, mock):
        """launch_test_application must be able to correctly classify a relative
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        relative_path = 'gedit'
        mixin.launch_test_application(relative_path)

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((relative_path,)))

    @patch('autopilot.introspection.qt.launch_application_from_desktop_file')
    def test_launch_can_classify_absolute_desktop_file_with_args(self, mock):
        """launch_test_application must be able to correctly classify an absolute
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        absolute_desktop_file = '/usr/share/applications/gedit.desktop'
        mixin.launch_test_application(absolute_desktop_file, "-some", "arguments")

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((absolute_desktop_file, "-some", "arguments")))

    @patch('autopilot.introspection.qt.launch_application_from_desktop_file')
    def test_launch_can_classify_relative_desktop_file_with_args(self, mock):
        """launch_test_application must be able to correctly classify a relative
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        relative_desktop_file = 'gedit.desktop'
        mixin.launch_test_application(relative_desktop_file, "-some", "arguments")

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((relative_desktop_file, "-some", "arguments")))

    @patch('autopilot.introspection.qt.launch_application_from_path')
    def test_launch_can_classify_absolute_app_path_with_args(self, mock):
        """launch_test_application must be able to correctly classify an absolute
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        absolute_path = '/usr/bin/gedit'
        mixin.launch_test_application(absolute_path, "-some", "arguments")

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((absolute_path, "-some", "arguments")))

    @patch('autopilot.introspection.qt.launch_application_from_path')
    def test_launch_can_classify_relative_app_path_with_args(self, mock):
        """launch_test_application must be able to correctly classify a relative
        path to a desktop file as a desktop file.

        """
        mixin = QtIntrospectionTestMixin()
        mixin.addCleanup = dummy_addCleanup

        relative_path = 'gedit'
        mixin.launch_test_application(relative_path, "-some", "arguments")

        self.assertThat(mock.called, Equals(True))
        self.assertThat(mock.call_args[0], Equals((relative_path, "-some", "arguments")))

    def test_launch_raises_ValueError_on_unknown_kwargs(self):
        """launch_test_application must raise ValueError when given unknown
        keyword arguments.

        """
        mixin = QtIntrospectionTestMixin()
        fn = lambda: mixin.launch_test_application('gedit', arg1=123, arg2='asd')
        self.assertThat(fn, raises(ValueError("Unknown keyword arguments: 'arg1', 'arg2'.")))

    def test_launch_raises_ValueError_on_unknown_kwargs_with_known(self):
        """launch_test_application must raise ValueError when given unknown
        keyword arguments.

        """
        mixin = QtIntrospectionTestMixin()
        fn = lambda: mixin.launch_test_application('gedit', arg1=123, arg2='asd', launch_dir='/')
        self.assertThat(fn, raises(ValueError("Unknown keyword arguments: 'arg1', 'arg2'.")))
