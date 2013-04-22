#!/bin/sh

#
# Build all the binary test applications.

set -e


build_qt_project () {
	cd qt
	if [ -e Makefile ]; then
		make distclean
	fi
	qmake -qt=$1
	make
	make install
	cd -
}

build_qt_project qt4
build_qt_project qt5
