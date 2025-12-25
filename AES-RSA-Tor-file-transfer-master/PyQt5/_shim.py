# internal shim that imports PySide6 and provides QtWidgets, QtCore, QtGui
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except Exception:
    # If PySide6 isn't installed, raise a clear ImportError so the caller can see
    raise ImportError("PySide6 is required (or install PyQt5). Please install PySide6 in the project's venv.")

# expose names used by the project
__all__ = ['QtWidgets', 'QtCore', 'QtGui']
