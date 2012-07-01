# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#

"""This module contains the code to retrieve state via DBus calls.

Under normal circumstances, the only thing you should need to use from this module
is the DBusIntrospectableObject class.

"""

from __future__ import absolute_import

from dbus import Interface
import logging
from testtools.matchers import Equals
from time import sleep

from autopilot.emulators.dbus_handler import session_bus

_object_registry = {}
logger = logging.getLogger(__name__)


class StateNotFoundError(RuntimeError):
    """Raised when a piece of state information from unity is not found."""

    message = "State not found for class with name '{}' and id '{}'."

    def __init__(self, class_name, class_id):
        super(StateNotFoundError, self).__init__(self.message.format(class_name, class_id))


class IntrospectableObjectMetaclass(type):
    """Metaclass to insert appropriate classes into the object registry."""

    def __new__(cls, classname, bases, classdict):
        """Add class name to type registry."""
        class_object = type.__new__(cls, classname, bases, classdict)
        _object_registry[classname] = class_object
        return class_object


INTROSPECTION_IFACE = 'com.canonical.Autopilot.Introspection'


def get_introspection_iface(service_name, object_path):
    """Get the autopilot introspection interface for the specified service name
    and object path.

    """
    if not isinstance(service_name, basestring):
        raise TypeError("Service name must be a string.")
    if not isinstance(object_path, basestring):
        raise TypeError("Object name must be a string")

    _debug_proxy_obj = session_bus.get_object(service_name, object_path)
    return Interface(_debug_proxy_obj, INTROSPECTION_IFACE)


def translate_state_keys(state_dict):
    """Translates the state_dict passed in so the keys are usable as python attributes."""
    return {k.replace('-','_'):v for k,v in state_dict.iteritems() }


def make_introspection_object(dbus_tuple):
    """Make an introspection object given a DBus tuple of (name, state_dict).

    This only works for classes that derive from DBusIntrospectionObject.
    """
    name, state = dbus_tuple
    try:
        class_type = _object_registry[name]
    except KeyError:
        logger.error("%s is not a valid introspection type!", name)
        return None
    return class_type(state)


class DBusIntrospectionObject(object):
    """A class that can be created using a dictionary of state from DBus.

    To use this class properly you must set the DBUS_SERVICE and DBUS_OBJECT
    class attributes. THey should be set to the Service name and object path
    where the autopilot interface is being exposed.

    """

    __metaclass__ = IntrospectableObjectMetaclass

    DBUS_SERVICE = None
    DBUS_OBJECT = None

    def __init__(self, state_dict):
        self.__state = {}
        self.set_properties(state_dict)

    def set_properties(self, state_dict):
        """Creates and set attributes of `self` based on contents of `state_dict`.

        Translates '-' to '_', so a key of 'icon-type' for example becomes 'icon_type'.

        """
        self.__state = {}
        for key, value in translate_state_keys(state_dict).iteritems():
            # don't store id in state dictionary -make it a proper instance attribute
            if key == 'id':
                self.id = value
            self.__state[key] = self._make_attribute(key, value)

    def _make_attribute(self, name, value):
        """Make an attribute for 'value', patched with the wait_for function."""

        def wait_for(self, expected_value):
            """Wait up to 10 seconds for our value to change to 'expected_value'.

            expected_value can be a testtools.matcher.Matcher subclass (like
            LessThan, for example), or an ordinary value.

            This works by refreshing the value using repeated dbus calls.

            Raises RuntimeError if the attribute was not equal to the expected value
            after 10 seconds.

            """
            # It's guaranteed that our value is up to date, since __getattr__ calls
            # refresh_state. This if statement stops us waiting if the value is
            # already what we expect:
            if self == expected_value:
                return

            # unfortunately not all testtools matchers derive from the Matcher
            # class, so we can't use issubclass, isinstance for this:
            match_fun = getattr(expected_value, 'match', None)
            is_matcher = match_fun and callable(match_fun)
            if not is_matcher:
                expected_value = Equals(expected_value)

            for i in range(10):
                name, new_state = self.parent.get_new_state()
                new_state = translate_state_keys(new_state)
                new_value = new_state[self.name]
                # Support for testtools.matcher classes:
                mismatch = expected_value.match(new_value)
                if mismatch:
                    failure_msg = mismatch.describe()
                else:
                    self.parent.set_properties(new_state)
                    return

                sleep(1)

            raise AssertionError("After 10 seconds test on %s.%s failed: %s"
                % (self.parent.__class__.__name__, self.name, failure_msg))

        # This looks like magic, but it's really not. We're creating a new type
        # on the fly that derives from the type of 'value' with a couple of
        # extra attributes: wait_for is the wait_for method above. 'parent' and
        # 'name' are needed by the wait_for method.
        #
        # We can't use traditional meta-classes here, since the type we're
        # deriving from is only known at call time, not at parse time (we could
        # override __call__ in the meta class, but that doesn't buy us anything
        # extra).
        #
        # A better way to do this would be with functools.partial, which I tried
        # initially, but doesn't work well with bound methods.
        t = type(value)
        attrs = {'wait_for': wait_for, 'parent':self, 'name':name}
        return type(t.__name__, (t,), attrs)(value)

    def get_children_by_type(self, desired_type, **kwargs):
        """Get a list of children of the specified type.

        desired_type must be a subclass of DBusIntrospectionObject.

        Keyword arguments can be used to restrict returned instances. For example:

        >>> get_children_by_type(Launcher, monitor=1)

        ... will return only LauncherInstances that have an attribute 'monitor'
            that is equal to 1.

        """
        #TODO: if kwargs has exactly one item in it we should specify the
        # restriction in the XPath query, so it gets processed in the Unity C++
        # code rather than in Python.
        self.refresh_state()

        query = self.get_class_query_string() + "/*"
        state_dicts = self.get_state_by_path(query)
        instances = [make_introspection_object(i) for i in state_dicts]

        result = []
        for instance in instances:
            # Skip items that are not instances of the desired type:
            if not isinstance(instance, desired_type):
                continue
            #skip instances that fail attribute check:
            passed = True
            for attr, val in kwargs.iteritems():
                if not hasattr(instance, attr) or getattr(instance, attr) != val:
                    # Either attribute is not present, or is present but with
                    # the wrong value - don't add this instance to the results list.
                    passed = False
            if passed:
                result.append(instance)
        return result

    def refresh_state(self):
        """Refreshes the object's state from unity.

        raises StateNotFound if the object in unity has been destroyed.

        """
        name, new_state = self.get_new_state()
        self.set_properties(new_state)

    @classmethod
    def get_all_instances(cls):
        """Get all instances of this class that exist within the Unity state tree.

        For example, to get all the BamfLauncherIcons:

        icons = BamfLauncherIcons.get_all_instances()

        The return value is a list (possibly empty) of class instances.

        """
        cls_name = cls.__name__
        instances = cls.get_state_by_path("//%s" % (cls_name))
        return [make_introspection_object(i) for i in instances]

    def __getattr__(self, name):
        # avoid recursion if for some reason we have no state set (should never
        # happen).
        if name == '__state':
            raise AttributeError()

        if name in self.__state:
            self.refresh_state()
            return self.__state[name]
        # attribute not found.
        raise AttributeError("Attribute '%s' not found." % (name))

    @classmethod
    def get_state_by_path(cls, piece):
        """Get state for a particular piece of the state tree.

        'piece' is an XPath-like query that specifies which bit of the tree you
        want to look at.

        """
        if not isinstance(piece, basestring):
            raise TypeError("XPath query must be a string, not %r", type(piece))

        return get_introspection_iface(
            cls.DBUS_SERVICE,
            cls.DBUS_OBJECT
            ).GetState(piece)

    def get_new_state(self):
        """Retrieve a new state dictionary for this class instance.

        Note: The state keys in the returned dictionary are not translated.

        """
        try:
            return self.get_state_by_path(self.get_class_query_string())[0]
        except IndexError:
            raise StateNotFoundError(self.__class__.__name__, self.id)

    def get_class_query_string(self):
        """Get the XPath query string required to refresh this class's state."""
        return "//%s[id=%d]" % (self.__class__.__name__, self.id)



