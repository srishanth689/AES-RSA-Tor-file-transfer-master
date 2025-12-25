# local shim to allow 'from PyQt5 import QtWidgets' to work by re-exporting PySide6
from PySide6 import QtWidgets, QtCore, QtGui
# expose symbols used by the project
QtWidgets = QtWidgets
QtCore = QtCore
QtGui = QtGui
