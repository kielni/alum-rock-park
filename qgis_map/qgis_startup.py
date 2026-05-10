from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QAction, QShortcut
from qgis.PyQt.QtGui import QKeySequence
from qgis.utils import iface

def reload_project():
    path = QgsProject.instance().fileName()
    if path:
        QgsProject.instance().read(path)

def register():
    shortcut = QShortcut(QKeySequence("Ctrl+R"), iface.mainWindow())
    shortcut.activated.connect(reload_project)

iface.initializationCompleted.connect(register)
