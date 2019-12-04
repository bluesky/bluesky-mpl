import functools

import event_model
from traitlets.traitlets import Dict, DottedObjectName, List
from qtpy.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from qtpy.QtCore import QObject, Signal
from qtpy import QtCore, QtGui

from .figures import FigureManager
from .utils import (
    ConfigurableQWidget,
    ConfigurableQTabWidget,
)
from ..utils import load_config


@functools.lru_cache(maxsize=1)
def _get_teleporter():

    class Teleporter(QObject):
        name_doc_escape = Signal(str, dict, bool)
    return Teleporter


class QtAwareCallback:
    def __init__(self, *args, use_teleporter=None, **kwargs):
        if use_teleporter is None:
            import matplotlib
            use_teleporter = 'qt' in matplotlib.get_backend().lower()
        if use_teleporter:
            Teleporter = _get_teleporter()
            self.__teleporter = Teleporter()
            self.__teleporter.name_doc_escape.connect(self._dispatch)
        else:
            self.__teleporter = None
        super().__init__(*args, **kwargs)

    def __call__(self, name, doc, validate=False):
        if self.__teleporter is not None:
            self.__teleporter.name_doc_escape.emit(name, doc, validate)
        else:
            self._dispatch(name, doc, validate)


class QRunRouter(event_model.RunRouter, QtAwareCallback):
    ...

qApp = None

def _create_qApp():
    """
    Create QApplicaiton if one does not exist. Return QApplication.instance().
    
    Vendored from matplotlib.backends.backend_qt5 with changes:
    - Assume Qt5, removing tolerance for Qt4.
    - Applicaiton has been changed (matplotlib -> bluesky).
    """
    global qApp

    if qApp is None:
        app = QApplication.instance()
        if app is None:
            # check for DISPLAY env variable on X11 build of Qt
            try:
                from PyQt5 import QtX11Extras
                is_x11_build = True
            except ImportError:
                is_x11_build = False
            else:
                is_x11_build = hasattr(QtGui, "QX11Info")
            if is_x11_build:
                display = os.environ.get('DISPLAY')
                if display is None or not re.search(r':\d', display):
                    raise RuntimeError('Invalid DISPLAY variable')

            try:
                QApplication.setAttribute(
                    QtCore.Qt.AA_EnableHighDpiScaling)
            except AttributeError:  # Attribute only exists for Qt>=5.6.
                pass
            qApp = QApplication(["bluesky"])
            qApp.lastWindowClosed.connect(qApp.quit)
        else:
            qApp = app

    try:
        qApp.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    except AttributeError:
        pass


def start_viewer():
    import matplotlib
    matplotlib.use('Qt5Agg')
    _create_qApp()
    main_window = QMainWindow()
    viewer = Viewer()
    main_window.setCentralWidget(viewer)
    main_window.show()
    # Avoid letting main_window be garbage collected.
    viewer._main_window = main_window
    return viewer


class Viewer(QWidget):
    name_doc = Signal(str, dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QVBoxLayout()
        outer_tab_container = OuterTabContainer()
        layout.addWidget(outer_tab_container)
        self.setLayout(layout)
        self.name_doc.connect(outer_tab_container.run_router)

    def __call__(self, name, doc):
        self.name_doc.emit(name, doc)



class OuterTabContainer(ConfigurableQTabWidget):
    def __init__(self, *args, **kwargs):
        self.update_config(load_config())
        self.overplot = False
        self.run_router = QRunRouter(
            [self.get_tab_run_router])
        super().__init__(*args, **kwargs)

    def get_tab_run_router(self, name, doc):
        if self.overplot:
            tab = self.currentWidget()
        else:
            tab = InnerTabContainer()
            label = ''  # TODO: What should this be?
            self.addTab(tab, label)
        tab.run_router('start', doc)
        return [tab.run_router], []


class InnerTabContainer(ConfigurableQTabWidget):
    factories = List([FigureManager], config=True)
    handler_registry = Dict(DottedObjectName(), config=True)

    def __init__(self, *args, **kwargs):
        self.update_config(load_config())
        super().__init__(*args, **kwargs)
        self.run_router = QRunRouter(
            [factory(self.addTab) for factory in self.factories],
            handler_registry=self.handler_registry)
