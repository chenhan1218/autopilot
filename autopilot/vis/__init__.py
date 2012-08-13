import sys
from autopilot.vis.main_window import MainWindow
from PyQt4 import QtGui

def vis_main():
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
