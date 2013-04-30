# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


"""This module contains the code to retrieve state via DBus calls.

Under normal circumstances, the only thing you should need to use from this module
is the DBusIntrospectableObject class.

"""

from __future__ import absolute_import

from contextlib import contextmanager
from dbus import Interface
import logging
from testtools.matchers import Equals
from time import sleep
from textwrap import dedent

from autopilot.introspection.constants import AP_INTROSPECTION_IFACE
from autopilot.utilities import Timer


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
        # The DBusIntrospectionObject class always has Backend == None, since it's
        # not introspectable itself. We need to compensate for this...
        if class_object._Backend is not None:
            _object_registry[class_object._Backend] = {classname:class_object}
        return class_object


def clear_object_registry(target_backend):
    """Delete all class objects from the object registry for a single backend."""
    global _object_registry

    # NOTE: We used to do '_object_registry.clear()' here, but that causes issues
    # when trying to use the unity emulators together with an application backend
    # since the application launch code clears the object registry. This is a case
    # of the autopilot backend abstraction leaking through into the visible
    # implementation. I'm planning on fixing that, but it's a sizable amount of work.
    # Until that happens, we need to live with this hack: don't delete objects if
    # their DBus service name is com.canonical.Unity
    # - Thomi Richards
    to_delete = []
    for k,v in _object_registry.iteritems():
        if k == target_backend:
            to_delete.append(k)

    for k in to_delete:
        del _object_registry[k]


def translate_state_keys(state_dict):
    """Translates the *state_dict* passed in so the keys are usable as python attributes."""
    return {k.replace('-','_'):v for k,v in state_dict.iteritems() }


def get_classname_from_path(object_path):
    return object_path.split("/")[-1]


def object_passes_filters(instance, **kwargs):
    """Return true if *instance* satisifies all the filters present in kwargs."""
    with instance.no_automatic_refreshing():
        for attr, val in kwargs.iteritems():
            if not hasattr(instance, attr) or getattr(instance, attr) != val:
                # Either attribute is not present, or is present but with
                # the wrong value - don't add this instance to the results list.
                return False
    return True


class DBusIntrospectionObject(object):
    """A class that can be created using a dictionary of state from DBus.

    To use this class properly you must set the DBUS_SERVICE and DBUS_OBJECT
    class attributes. They should be set to the Service name and object path
    where the autopilot interface is being exposed.

    """

    __metaclass__ = IntrospectableObjectMetaclass

    _Backend = None

    def __init__(self, state_dict, path):
        self.__state = {}
        self.__refresh_on_attribute = True
        self.set_properties(state_dict)
        self.path = path

    def set_properties(self, state_dict):
        """Creates and set attributes of *self* based on contents of *state_dict*.

        .. note:: Translates '-' to '_', so a key of 'icon-type' for example
         becomes 'icon_type'.

        """
        self.__state = {}
        for key, value in translate_state_keys(state_dict).iteritems():
            # don't store id in state dictionary -make it a proper instance attribute
            if key == 'id':
                self.id = value
            self.__state[key] = self._make_attribute(key, value)

    def _make_attribute(self, name, value):
        """Make an attribute for *value*, patched with the wait_for function."""

        def wait_for(self, expected_value, timeout=10):
            """Wait up to 10 seconds for our value to change to *expected_value*.

            *expected_value* can be a testtools.matcher. Matcher subclass (like
            LessThan, for example), or an ordinary value.

            This works by refreshing the value using repeated dbus calls.

            :raises: **RuntimeError** if the attribute was not equal to the
             expected value after 10 seconds.

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


            time_left = timeout
            while True:
                _, new_state = self.parent.get_new_state()
                new_state = translate_state_keys(new_state)
                new_value = new_state[self.name]
                # Support for testtools.matcher classes:
                mismatch = expected_value.match(new_value)
                if mismatch:
                    failure_msg = mismatch.describe()
                else:
                    self.parent.set_properties(new_state)
                    return

                if time_left >= 1:
                    sleep(1)
                    time_left -= 1
                else:
                    sleep(time_left)
                    break

            raise AssertionError("After %.1f seconds test on %s.%s failed: %s"
                % (timeout, self.parent.__class__.__name__, self.name, failure_msg))

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

        Keyword arguments can be used to restrict returned instances. For example:

        >>> get_children_by_type(Launcher, monitor=1)

        will return only LauncherInstances that have an attribute 'monitor' that
        is equal to 1. The type can also be specified as a string, which is
        useful if there is no emulator class specified:

        >>> get_children_by_type('Launcher', monitor=1)

        Note however that if you pass a string, and there is an emulator class
        defined, autopilot will not use it.

        :param desired_type:
        :type desired_type: subclass of DBusIntrospectionObject, or a string.

        .. important:: *desired_type* **must** be a subclass of
         DBusIntrospectionObject.

        """
        #TODO: if kwargs has exactly one item in it we should specify the
        # restriction in the XPath query, so it gets processed in the Unity C++
        # code rather than in Python.
        instances = self.get_children()

        result = []
        for instance in instances:
            # Skip items that are not instances of the desired type:
            if isinstance(desired_type, basestring):
                if instance.__class__.__name__ != desired_type:
                    continue
            elif not isinstance(instance, desired_type):
                continue

            #skip instances that fail attribute check:
            if object_passes_filters(instance, **kwargs):
                result.append(instance)
        return result

    def get_properties(self):
        """Returns a dictionary of all the properties on this class."""
        # Since we're grabbing __state directly there's no implied state
        # refresh, so do it manually:
        self.refresh_state()
        props = self.__state.copy()
        props['id'] = self.id
        return props

    def get_children(self):
        """Returns a list of all child objects."""
        self.refresh_state()

        query = self.get_class_query_string() + "/*"
        state_dicts = self.get_state_by_path(query)
        children = [self.make_introspection_object(i) for i in state_dicts]
        return children

    def select_single(self, type_name='*', **kwargs):
        """Get a single node from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.
        You must specify either *type_name*, keyword filters or both.

        Searches recursively from the node this method is called on. For
        example:

        >>> app.select_single('QPushButton', objectName='clickme')
        ... returns a QPushButton whose 'objectName' property is 'clickme'.

        If nothing is returned from the query, this method returns None.

        :raises: **ValueError** if the query returns more than one item. *If you
         want more than one item, use select_many instead*.

        :raises: **TypeError** if neither *type_name* or keyword filters are
        provided.

        """
        instances = self.select_many(type_name, **kwargs)
        if len(instances) > 1:
            raise ValueError("More than one item was returned for query")
        if not instances:
            return None
        return instances[0]

    def select_many(self, type_name='*', **kwargs):
        """Get a list of nodes from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.
        You must specify either *type_name*, keyword filters or both.

        Searches recursively from the node this method is called on.

        For example:

        >>> app.select_many('QPushButton', enabled=True)
        ... returns a list of QPushButtons that are enabled.

        >>> file_menu = app.select_one('QMenu', title='File')
        >>> file_menu.select_many('QAction')
        ... returns a list of QAction objects who appear below file_menu in the
        object tree.

        If you only want to get one item, use select_single instead.

        :raises: **TypeError** if neither *type_name* or keyword filters are
        provided.

        """
        if type_name == "*" and not kwargs:
            raise TypeError("You must specify either a type name or a filter.")

        logger.debug("Selecting objects of %s with attributes: %r",
            'any type' if type_name == '*' else 'type ' + type_name,
            kwargs)

        first_param = ''
        if kwargs:
            first_param = '[{}={}]'.format(*kwargs.popitem())
        query_path = "%s//%s%s" % (self.get_class_query_string(),
                                   type_name,
                                   first_param)

        state_dicts = self.get_state_by_path(query_path)
        instances = [self.make_introspection_object(i) for i in state_dicts]
        return filter(lambda i: object_passes_filters(i, **kwargs), instances)

    def refresh_state(self):
        """Refreshes the object's state from unity.

        :raises: **StateNotFound** if the object in unity has been destroyed.

        """
        _, new_state = self.get_new_state()
        self.set_properties(new_state)

    @classmethod
    def get_all_instances(cls):
        """Get all instances of this class that exist within the Unity state tree.

        For example, to get all the BamfLauncherIcons:

        >>> icons = BamfLauncherIcons.get_all_instances()

        :return: List (possibly empty) of class instances.

        WARNING: Using this method is slow - it requires a complete scan of the
        introspection tree. Instead, get the root tree object with
        get_root_instance, and then navigate to the desired node.

        """
        cls_name = cls.__name__
        instances = cls.get_state_by_path("//%s" % (cls_name))
        return [cls.make_introspection_object(i) for i in instances]

    @classmethod
    def get_root_instance(cls) :
        """Get the object at the root of this tree."""
        instances = cls.get_state_by_path("/")
        if len(instances) != 1:
            logger.error("Could not retrieve root object.")
            return None
        return cls.make_introspection_object(instances[0])

    def __getattr__(self, name):
        # avoid recursion if for some reason we have no state set (should never
        # happen).
        if name == '__state':
            raise AttributeError()

        if name in self.__state:
            if self.__refresh_on_attribute:
                self.refresh_state()
            return self.__state[name]
        # attribute not found.
        raise AttributeError("Class '%s' has no attribute '%s'." %
            (self.__class__.__name__, name))

    @classmethod
    def get_state_by_path(cls, piece):
        """Get state for a particular piece of the state tree.

        *piece* is an XPath-like query that specifies which bit of the tree you
        want to look at.

        :param string piece:
        :raises: **TypeError** on invalid *piece* parameter.

        """
        if not isinstance(piece, basestring):
            raise TypeError("XPath query must be a string, not %r", type(piece))

        with Timer("GetState %s" % piece):
            return cls._Backend.introspection_iface.GetState(piece)

    def get_new_state(self):
        """Retrieve a new state dictionary for this class instance.

        .. note:: The state keys in the returned dictionary are not translated.

        """
        try:
            return self.get_state_by_path(self.get_class_query_string())[0]
        except IndexError:
            raise StateNotFoundError(self.__class__.__name__, self.id)

    def get_class_query_string(self):
        """Get the XPath query string required to refresh this class's state."""
        return self.path + "[id=%d]" % self.id

    @classmethod
    def make_introspection_object(cls, dbus_tuple):
        """Make an introspection object given a DBus tuple of (path, state_dict).

        This only works for classes that derive from DBusIntrospectionObject.
        """
        path, state = dbus_tuple
        name = get_classname_from_path(path)
        try:
            class_type = _object_registry[cls._Backend][name]
        except KeyError:
            logger.warning("Generating introspection instance for type '%s' based on generic class.", name)
            class_type = type(str(name), (cls,), {})
        return class_type(state, path)

    @contextmanager
    def no_automatic_refreshing(self):
        """Context manager function to disable automatic DBus refreshing when retrieving attributes.

        Example usage:

        >>> with instance.no_automatic_refreshing():
            # access lots of attributes.

        """
        try:
            self.__refresh_on_attribute = False
            yield
        finally:
            self.__refresh_on_attribute = True
