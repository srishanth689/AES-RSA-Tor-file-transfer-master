# Compatibility shim: re-export PySide6 modules as PyQt5
from . import _shim
for name in dir(_shim):
    if not name.startswith("_"):
        globals()[name] = getattr(_shim, name)
