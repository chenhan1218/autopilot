# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# Copyright 2012 Canonical
# Author: Thomi Richards
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
from __future__ import absolute_import

import dbus
from PyQt4 import QtGui, QtCore

from autopilot.introspection.dbus import (
    DBusIntrospectionObject,
    AP_INTROSPECTION_IFACE,
    StateNotFoundError
    )
from autopilot.introspection.qt import (
    make_proxy_object_from_service_name,
    QtObjectProxyMixin,
    )


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.selectable_interfaces = {}
        self.initUI()
        self.readSettings()

    def readSettings(self):
        settings = QtCore.QSettings()
        self.restoreGeometry(settings.value("geometry").toByteArray());
        self.restoreState(settings.value("windowState").toByteArray());

    def closeEvent(self, event):
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def initUI(self):
        header_titles = QtCore.QStringList(["Name", "Value"])

        self.statusBar().showMessage('Waiting for first valid dbus connection')

        self.splitter = QtGui.QSplitter(self)
        self.tree_view = QtGui.QTreeView(self.splitter)

        self.details_frame = QtGui.QFrame(self.splitter)
        self.details_layout = QtGui.QVBoxLayout(self.details_frame)
        self.details_layout.addWidget(QtGui.QLabel("Properties:"))
        self.table_view = QtGui.QTableWidget()
        self.table_view.setColumnCount(2)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setHorizontalHeaderLabels(header_titles)
        self.table_view.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.details_layout.addWidget(self.table_view)

        self.signals_label = QtGui.QLabel("Signals:")
        self.details_layout.addWidget(self.signals_label)

        self.signals_table = QtGui.QTableWidget()
        self.signals_table.setColumnCount(1)
        self.signals_table.verticalHeader().setVisible(False)
        self.signals_table.setAlternatingRowColors(True)
        self.signals_table.setHorizontalHeaderLabels(["Signal Signature"])
        self.signals_table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.details_layout.addWidget(self.signals_table)

        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 100)
        self.setCentralWidget(self.splitter)

        self.show_signal_table(False)

        self.connection_list = QtGui.QComboBox()
        self.connection_list.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        self.connection_list.activated.connect(self.conn_list_activated)

        self.toolbar = self.addToolBar('Connection')
        self.toolbar.setObjectName('Connection Toolbar')
        self.toolbar.addWidget(self.connection_list)

    def show_signal_table(self, show):
        """Show or hide the signals table & label."""
        self.signals_label.setVisible(show)
        self.signals_table.setVisible(show)

    def on_interface_found(self, conn, obj, iface):
        if iface == AP_INTROSPECTION_IFACE:
            self.statusBar().showMessage('Updating connection list')
            try:
                proxy_object = make_proxy_object_from_service_name(conn, obj)
                cls_name = proxy_object.__class__.__name__
                if not self.selectable_interfaces.has_key(cls_name):
                    self.selectable_interfaces[cls_name] = proxy_object
                    self.update_selectable_interfaces()
            except (dbus.DBusException, RuntimeError):
                pass
            self.statusBar().clearMessage()

    def update_selectable_interfaces(self):
        selected_text = self.connection_list.currentText()
        self.connection_list.clear()
        self.connection_list.addItem("Please select a connection",
                                     QtCore.QVariant(None))
        for name, proxy_obj in self.selectable_interfaces.iteritems():
            if isinstance(proxy_obj, QtObjectProxyMixin):
                self.connection_list.addItem(
                    QtGui.QIcon(":/trolltech/qmessagebox/images/qtlogo-64.png"),
                    name,
                    QtCore.QVariant(proxy_obj)
                    )
            else:
                self.connection_list.addItem(name, QtCore.QVariant(proxy_obj))

        prev_selected = self.connection_list.findText(selected_text,
                                                      QtCore.Qt.MatchExactly)
        if prev_selected == -1:
            prev_selected = 0
        self.connection_list.setCurrentIndex(prev_selected)

    def conn_list_activated(self, index):
        dbus_details = self.connection_list.itemData(index).toPyObject()
        if dbus_details:
            self.tree_model = VisTreeModel(dbus_details)
            self.tree_view.setModel(self.tree_model)
            self.tree_view.selectionModel().currentChanged.connect(self.tree_item_changed)

    def tree_item_changed(self, current, previous):
        proxy = current.internalPointer().dbus_object
        self.update_object_detals_table_from_proxy_object(proxy)
        if isinstance(proxy, QtObjectProxyMixin):
            self.update_object_signals_from_proxy_object(proxy)
            self.show_signal_table(True)
        else:
            self.show_signal_table(False)

    def update_object_detals_table_from_proxy_object(self, proxy_object):
        """Update the object details table."""
        self.table_view.setSortingEnabled(False)
        self.table_view.clearContents()
        object_details = proxy_object.get_properties()
        # remove the Children property - we don't care about it:
        object_details.pop("Children", None)
        self.table_view.setRowCount(len(object_details))
        for i, key in enumerate(object_details):
            details_string = dbus_string_rep(object_details[key])
            item_name = QtGui.QTableWidgetItem(key)
            item_details = QtGui.QTableWidgetItem(details_string)
            self.table_view.setItem(i, 0, item_name)
            self.table_view.setItem(i, 1, item_details)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.table_view.resizeColumnsToContents()

    def update_object_signals_from_proxy_object(self, proxy_object):
        """Update the object signals table."""
        self.signals_table.setSortingEnabled(False)
        self.signals_table.clearContents()
        signals = proxy_object.get_signals()
        self.signals_table.setRowCount(len(signals))
        for i, signal in enumerate(signals):
            self.signals_table.setItem(i, 0, QtGui.QTableWidgetItem(str(signal)))
        self.signals_table.setSortingEnabled(True)
        self.signals_table.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.signals_table.resizeColumnsToContents()


def dbus_string_rep(dbus_type):
    """Get a string representation of various dbus types."""
    if isinstance(dbus_type, dbus.Boolean):
        return repr(bool(dbus_type))
    if isinstance(dbus_type, dbus.String):
        return dbus_type.encode('ascii', errors='ignore')
    if (isinstance(dbus_type, dbus.Int16)
        or isinstance(dbus_type, dbus.UInt16)
        or isinstance(dbus_type, dbus.Int32)
        or isinstance(dbus_type, dbus.UInt32)
        or isinstance(dbus_type, dbus.Int64)
        or isinstance(dbus_type, dbus.UInt64)):
        return repr(int(dbus_type))
    if isinstance(dbus_type, dbus.Double):
        return repr(float(dbus_type))
    if (isinstance(dbus_type, dbus.Array)
        or isinstance(dbus_type, dbus.Struct)):
        return ', '.join([dbus_string_rep(i) for i in dbus_type])
    else:
        return repr(dbus_type)


class TreeNode(object):
    """Used to represent the tree data structure that is the backend of the
    treeview.

    Lazy loads a nodes children instead of waiting to load and store a static
    snapshot of the apps whole state.

    """
    def __init__(self, parent=None, name='', dbus_object=None):
        self.parent = parent
        self.name = name
        self.dbus_object = dbus_object
        self._children = []

    @property
    def children(self):
        if not self._children:
            try:
                for child in self.dbus_object.get_children():
                    name = child.__class__.__name__
                    self._children.append(TreeNode(self, name, child))
            except StateNotFoundError:
                pass
        return self._children


class VisTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, introspectable_obj):
        super(VisTreeModel, self).__init__()
        name = introspectable_obj.__class__.__name__
        self.tree_root = TreeNode(name=name, dbus_object=introspectable_obj)

    def index(self, row, col, parent):
        if not self.hasIndex(row, col, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parentItem = self.tree_root
        else:
            parentItem = parent.internalPointer()

        try:
            childItem = parentItem.children[row]
            return self.createIndex(row, col, childItem)
        except IndexError:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QtCore.QModelIndex()

        parentItem = childItem.parent

        if parentItem == self.tree_root:
            return QtCore.QModelIndex()

        row = parentItem.children.index(childItem)
        return self.createIndex(row, 0, parentItem)

    def rowCount(self, parent):
        if not parent.isValid():
            p_Item = self.tree_root
        else:
            p_Item = parent.internalPointer()
        return len(p_Item.children)

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        if role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(index.internalPointer().name)

    def headerData(self, column, orientation, role):
        if (orientation == QtCore.Qt.Horizontal and
            role == QtCore.Qt.DisplayRole):
            try:
                return QtCore.QVariant("Tree Node")
            except IndexError:
                pass

        return QtCore.QVariant()