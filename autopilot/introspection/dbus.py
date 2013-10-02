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

Under normal circumstances, the only thing you should need to use from this
module is the DBusIntrospectableObject class.

"""

from __future__ import absolute_import

from contextlib import contextmanager
import logging
import re
from testtools.matchers import Equals
from time import sleep
from uuid import uuid4

from autopilot.utilities import Timer, get_debug_logger


_object_registry = {}
logger = logging.getLogger(__name__)


class StateNotFoundError(RuntimeError):

    """Raised when a piece of state information is not found.

    This exception is commonly raised when the application has destroyed (or
    not yet created) the object you are trying to access in autopilot. This
    typically happens for a number of possible reasons:

     * The UI widget you are trying to access with
        :py:met:`DBusIntrospectionObject.select_single` or
        :py:met:`DBusIntrospectionObject.select_single` does not exist yet.
    * The UI widget you are trying to access has been destroyed by the
        application.

    """

    def __init__(self, class_name=None, **filters):
        """Construct a StateNotFoundError.

        :raises ValueError: if neither the class name not keyword arguments
            are specified.

        """
        if class_name is None and not filters:
            raise ValueError("Must specify either class name or filters.")

        if class_name is None:
            self._message = \
                u"State not found with filters {}.".format(
                    repr(filters)
                )
        elif not filters:
            self._message = u"State not found for class '{}'.".format(
                class_name
            )
        else:
            self._message = \
                u"State not found for class '{}' and filters {}.".format(
                    class_name,
                    repr(filters)
                )

    def __str__(self):
        return self._message.encode('utf8')

    def __unicode__(self):
        return self._message


class IntrospectableObjectMetaclass(type):
    """Metaclass to insert appropriate classes into the object registry."""

    def __new__(cls, classname, bases, classdict):
        """Add class name to type registry."""
        class_object = type.__new__(cls, classname, bases, classdict)
        if classname in (
            'ApplicationProxyObject',
            'CustomEmulatorBase',
            'DBusIntrospectionObject',
        ):
            return class_object

        if getattr(class_object, '_id', None) is not None:
            if class_object._id in _object_registry:
                _object_registry[class_object._id][classname] = class_object
            else:
                _object_registry[class_object._id] = {classname: class_object}
        return class_object


def translate_state_keys(state_dict):
    """Translates the *state_dict* passed in so the keys are usable as python
    attributes."""
    return {k.replace('-', '_'): v for k, v in state_dict.iteritems()}


def get_classname_from_path(object_path):
    return object_path.split("/")[-1]


def object_passes_filters(instance, **kwargs):
    """Return true if *instance* satisifies all the filters present in
    kwargs."""
    with instance.no_automatic_refreshing():
        for attr, val in kwargs.iteritems():
            if not hasattr(instance, attr) or getattr(instance, attr) != val:
                # Either attribute is not present, or is present but with
                # the wrong value - don't add this instance to the results
                # list.
                return False
    return True


class DBusIntrospectionObject(object):
    """A class that supports transparent data retrieval from the application
    under test.

    This class is the base class for all objects retrieved from the application
    under test. It handles transparently refreshing attribute values when
    needed, and contains many methods to select child objects in the
    introspection tree.

    """

    __metaclass__ = IntrospectableObjectMetaclass

    def __init__(self, state_dict, path, backend):
        self.__state = {}
        self.__refresh_on_attribute = True
        self._set_properties(state_dict)
        self._path = path
        self._backend = backend

    def _set_properties(self, state_dict):
        """Creates and set attributes of *self* based on contents of
        *state_dict*.

        .. note:: Translates '-' to '_', so a key of 'icon-type' for example
         becomes 'icon_type'.

        """
        self.__state = {}
        for key, value in translate_state_keys(state_dict).iteritems():
            # don't store id in state dictionary -make it a proper instance
            # attribute
            if key == 'id':
                self.id = value
            self.__state[key] = self._make_attribute(key, value)

    def _make_attribute(self, name, value):
        """Make an attribute for *value*, patched with the wait_for
        function."""

        def wait_for(self, expected_value, timeout=10):
            """Wait up to 10 seconds for our value to change to
            *expected_value*.

            *expected_value* can be a testtools.matcher. Matcher subclass (like
            LessThan, for example), or an ordinary value.

            This works by refreshing the value using repeated dbus calls.

            :raises: **RuntimeError** if the attribute was not equal to the
             expected value after 10 seconds.

            """
            # It's guaranteed that our value is up to date, since __getattr__
            # calls refresh_state. This if statement stops us waiting if the
            # value is already what we expect:
            if self == expected_value:
                return

            def make_unicode(value):
                if isinstance(value, str):
                    return unicode(value.decode('utf8'))
                return value

            if hasattr(expected_value, 'expected'):
                expected_value.expected = make_unicode(expected_value.expected)

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
                new_value = make_unicode(new_state[self.name])
                # Support for testtools.matcher classes:
                mismatch = expected_value.match(new_value)
                if mismatch:
                    failure_msg = mismatch.describe()
                else:
                    self.parent._set_properties(new_state)
                    return

                if time_left >= 1:
                    sleep(1)
                    time_left -= 1
                else:
                    sleep(time_left)
                    break

            raise AssertionError(
                "After %.1f seconds test on %s.%s failed: %s" % (
                    timeout, self.parent.__class__.__name__, self.name,
                    failure_msg))

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
        # A better way to do this would be with functools.partial, which I
        # tried initially, but doesn't work well with bound methods.
        t = type(value)
        attrs = {'wait_for': wait_for, 'parent': self, 'name': name}
        return type(t.__name__, (t,), attrs)(value)

    def get_children_by_type(self, desired_type, **kwargs):
        """Get a list of children of the specified type.

        Keyword arguments can be used to restrict returned instances. For
        example:

        >>> get_children_by_type(Launcher, monitor=1)

        will return only Launcher instances that have an attribute 'monitor'
        that is equal to 1. The type can also be specified as a string, which
        is useful if there is no emulator class specified:

        >>> get_children_by_type('Launcher', monitor=1)

        Note however that if you pass a string, and there is an emulator class
        defined, autopilot will not use it.

        :param desired_type: Either a string naming the type you want, or a
            class of the type you want (the latter is used when defining
            custom emulators)

        .. seealso::
            Tutorial Section :ref:`custom_emulators`

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
        """Returns a dictionary of all the properties on this class.

        This can be useful when you want to log all the properties exported
        from your application for a particular object. Every property in the
        returned dictionary can be accessed as attributes of the object as
        well.

        """
        # Since we're grabbing __state directly there's no implied state
        # refresh, so do it manually:
        self.refresh_state()
        props = self.__state.copy()
        props['id'] = self.id
        return props

    def get_children(self):
        """Returns a list of all child objects.

        This returns a list of all children. To return only children of a
        specific type, use :meth:`get_children_by_type`. To get objects
        further down the introspection tree (i.e.- nodes that may not
        necessarily be immeadiate children), use :meth:`select_single` and
        :meth:`select_many`.

        """
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

        This method searches recursively from the instance this method is
        called on. Calling :meth:`select_single` on the application (root)
        proxy object will search the entire tree. Calling
        :meth:`select_single` on an object in the tree will only search it's
        descendants.

        Example usage::

            app.select_single('QPushButton', objectName='clickme')
            # returns a QPushButton whose 'objectName' property is 'clickme'.

        If nothing is returned from the query, this method returns None.

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :raises ValueError: if the query returns more than one item. *If
            you want more than one item, use select_many instead*.

        :raises TypeError: if neither *type_name* or keyword filters are
            provided.

        .. seealso::
            Tutorial Section :ref:`custom_emulators`

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

        This method searches recursively from the instance this method is
        called on. Calling :meth:`select_many` on the application (root) proxy
        object will search the entire tree. Calling :meth:`select_many` on an
        object in the tree will only search it's descendants.

        Example Usage::

            app.select_many('QPushButton', enabled=True)
            # returns a list of QPushButtons that are enabled.

        As mentioned above, this method searches the object tree recurseivly::
            file_menu = app.select_one('QMenu', title='File')
            file_menu.select_many('QAction')
            # returns a list of QAction objects who appear below file_menu in
            the object tree.

        If you only want to get one item, use :meth:`select_single` instead.

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :raises: **TypeError** if neither *type_name* or keyword filters are
            provided.

        .. seealso::
            Tutorial Section :ref:`custom_emulators`

        """
        if not isinstance(type_name, str) and issubclass(
                type_name, DBusIntrospectionObject):
            type_name = type_name.__name__

        if type_name == "*" and not kwargs:
            raise TypeError("You must specify either a type name or a filter.")

        logger.debug(
            "Selecting objects of %s with attributes: %r",
            'any type' if type_name == '*' else 'type ' + type_name, kwargs)

        first_param = ''
        for k, v in kwargs.iteritems():
            # LP Bug 1209029: The XPathSelect protocol does not allow all valid
            # node names or values. We need to decide here whether the filter
            # parameters are going to work on the backend or not. If not, we
            # just do the processing client-side. See the
            # _is_valid_server_side_filter_param function (below) for the
            # specific requirements.
            if _is_valid_server_side_filter_param(k, v):
                first_param = '[{}={}]'.format(k, v)
                kwargs.pop(k)
                break
        query_path = "%s//%s%s" % (self.get_class_query_string(),
                                   type_name,
                                   first_param)

        state_dicts = self.get_state_by_path(query_path)
        instances = [self.make_introspection_object(i) for i in state_dicts]
        return filter(lambda i: object_passes_filters(i, **kwargs), instances)

    def refresh_state(self):
        """Refreshes the object's state from unity.

        You should probably never have to call this directly. Autopilot
        automatically retrieves new state every time this object's attributes
        are read.

        :raises: **StateNotFound** if the object in unity has been destroyed.

        """
        _, new_state = self.get_new_state()
        self._set_properties(new_state)

    def get_all_instances(self):
        """Get all instances of this class that exist within the Application
        state tree.

        For example, to get all the LauncherIcon instances:

        >>> icons = LauncherIcon.get_all_instances()

        .. warning::
            Using this method is slow - it requires a complete scan of the
            introspection tree. You should only use this when you're not sure
            where the objects you are looking for are located. Depending on
            the application you are testing, you may get duplicate results
            using this method.

        :return: List (possibly empty) of class instances.

        """
        cls_name = type(self).__name__
        instances = self.get_state_by_path("//%s" % (cls_name))
        return [self.make_introspection_object(i) for i in instances]

    def get_root_instance(self):
        """Get the object at the root of this tree.

        This will return an object that represents the root of the
        introspection tree.

        """
        instances = self.get_state_by_path("/")
        if len(instances) != 1:
            logger.error("Could not retrieve root object.")
            return None
        return self.make_introspection_object(instances[0])

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
        raise AttributeError(
            "Class '%s' has no attribute '%s'." %
            (self.__class__.__name__, name))

    def get_state_by_path(self, piece):
        """Get state for a particular piece of the state tree.

        You should probably never need to call this directly.

        :param piece: an XPath-like query that specifies which bit of the tree
            you want to look at.
        :raises: **TypeError** on invalid *piece* parameter.

        """
        if not isinstance(piece, basestring):
            raise TypeError(
                "XPath query must be a string, not %r", type(piece))

        with Timer("GetState %s" % piece):
            data = self._backend.introspection_iface.GetState(piece)
            if len(data) > 15:
                logger.warning(
                    "Your query '%s' returned a lot of data (%d items). This "
                    "is likely to be slow. You may want to consider optimising"
                    " your query to return fewer items.",
                    piece,
                    len(data)
                )
            return data

    def get_new_state(self):
        """Retrieve a new state dictionary for this class instance.

        You should probably never need to call this directly.

        .. note:: The state keys in the returned dictionary are not translated.

        """
        try:
            return self.get_state_by_path(self.get_class_query_string())[0]
        except IndexError:
            raise StateNotFoundError(self.__class__.__name__, id=self.id)

    def get_class_query_string(self):
        """Get the XPath query string required to refresh this class's
        state."""
        if not self._path.startswith('/'):
            return "//" + self._path + "[id=%d]" % self.id
        else:
            return self._path + "[id=%d]" % self.id

    def make_introspection_object(self, dbus_tuple):
        """Make an introspection object given a DBus tuple of
        (path, state_dict).

        This only works for classes that derive from DBusIntrospectionObject.
        """
        path, state = dbus_tuple
        name = get_classname_from_path(path)
        try:
            class_type = _object_registry[self._id][name]
        except KeyError:
            get_debug_logger().warning(
                "Generating introspection instance for type '%s' based on "
                "generic class.", name)
            # we want the object to inherit from the custom emulator base, not
            # the object class that is doing the selecting
            for base in type(self).__bases__:
                if issubclass(base, CustomEmulatorBase):
                    base_class = base
                    break
            else:
                base_class = type(self)
            class_type = type(str(name), (base_class,), {})
        return class_type(state, path, self._backend)

    @contextmanager
    def no_automatic_refreshing(self):
        """Context manager function to disable automatic DBus refreshing when
        retrieving attributes.

        Example usage:

        >>> with instance.no_automatic_refreshing():
            # access lots of attributes.

        This can be useful if you need to check lots of attributes in a tight
        loop, or if you want to atomicaly check several attributes at once.

        """
        try:
            self.__refresh_on_attribute = False
            yield
        finally:
            self.__refresh_on_attribute = True


def _is_valid_server_side_filter_param(key, value):
    """Return True if the key and value parameters are valid for server-side
    processing.

    """
    return (
        isinstance(value, str) and
        re.match(r'^[a-zA-Z0-9_\-]+( [a-zA-Z0-9_\-])*$', key) is not None and
        re.match(r'^[a-zA-Z0-9_\-]+( [a-zA-Z0-9_\-])*$', value) is not None)


class _CustomEmulatorMeta(IntrospectableObjectMetaclass):

    def __new__(cls, name, bases, d):
        # only consider classes derived from CustomEmulatorBase
        if name != 'CustomEmulatorBase':
            # and only if they don't already have an Id set.
            have_id = False
            for base in bases:
                if hasattr(base, '_id'):
                    have_id = True
                    break
            if not have_id:
                d['_id'] = uuid4()
        return super(_CustomEmulatorMeta, cls).__new__(cls, name, bases, d)


class CustomEmulatorBase(DBusIntrospectionObject):

    """This class must be used as a base class for any custom emulators defined
    within a test case.

    .. seealso::
        Tutorial Section :ref:`custom_emulators`
            Information on how to write custom emulators.
    """

    __metaclass__ = _CustomEmulatorMeta
