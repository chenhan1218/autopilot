TEMPLATE = app

contains(QT_VERSION, ^5\\..\\..*) {
	message("Building for Qt5")
    TARGET = qt5testapp
    QT += widgets quick
    qmlfile.files = qt5.qml
    DEFINES += QT5_SUPPORT
} else {
	message("Building for Qt4")
	TARGET = qt4testapp
	QT += declarative
	qmlfile.files += qt4.qml
}

SOURCES += testapp.cpp

qmlfile.path=..

target.path=..
target.file = $TARGET

INSTALLS += qmlfile target
