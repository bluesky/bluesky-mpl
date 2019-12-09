import collections.abc
import functools
import itertools
import os
import re

import event_model
import matplotlib
from traitlets.traitlets import Dict, DottedObjectName, List
from qtpy.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout
from qtpy.QtCore import QObject, Signal
from qtpy import QtCore, QtGui

from .figures import FigureDispatcher
from .utils import (
    ConfigurableQObject,
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
                from PyQt5 import QtX11Extras  # noqa
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
    matplotlib.use('Qt5Agg')
    _create_qApp()
    main_window = QMainWindow()
    viewer = Viewer()
    main_window.setCentralWidget(viewer)
    main_window.show()
    # Avoid letting main_window be garbage collected.
    viewer._main_window = main_window
    return viewer


class TabsView(collections.abc.Mapping):
    def __init__(self, tabs):
        self._tabs = tabs

    def __repr__(self):
        return f"TabsView({self._tabs!r})"

    def __getitem__(self, key):
        return self._tabs[key]

    def __iter__(self):
        yield from self._tabs

    def __len__(self):
        return len(self._tabs)

    def __setitem__(self, key, value):
        raise TypeError(
            "The tabs cannot be edited directly. "
            "Instead, use the method Viewer.add_tab.")

    def __delitem__(self, key):
        raise TypeError(
            "The tabs cannot be edited directly. "
            "Instead, use the method Viewer.remove_tab.")


class Viewer(QWidget):
    name_doc = Signal(str, dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QVBoxLayout()
        self._viewer_tab_container = ViewerTabContainer()
        layout.addWidget(self._viewer_tab_container)
        self.setLayout(layout)
        self.name_doc.connect(self._viewer_tab_container.run_router)
        self.tabs = TabsView(self._viewer_tab_container.tabs)

    def __call__(self, name, doc):
        self.name_doc.emit(name, doc)

    def add_tab(self, label):
        return self._viewer_tab_container.add_tab(label)

    def add_run(self, run, fill='delayed'):
        for name, doc in run.canonical(fill=fill):
            self.name_doc.emit(name, doc)


class ViewerTabContainer(QTabWidget):
    name_doc = Signal(str, dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_router = QRunRouter([self.current_viewer_tab])
        self.tabs = {}

    def add_tab(self, label=None):
        if label in self.tabs:
            raise ValueError(f"Must be unique and {label} is already taken")
        elif label is None:
            for i in itertools.count():
                label = f'Untitled {i}'
                try:
                    return self.add_tab(label)
                except ValueError:
                    continue

        inner_tab_container = InnerTabContainer()
        self.addTab(inner_tab_container, label)

        def set_label(label):
            if label in self.tabs:
                raise ValueError(f"Must be unique and {label} is already taken")
            index = self.indexOf(inner_tab_container)
            old_label = self.tabText(index)
            del self.tabs[old_label]
            self.tabs[label] = viewer_tab
            self.setTabText(index, label)

        viewer_tab = ViewerTab(inner_tab_container, set_label)
        self.tabs[label] = viewer_tab
        return viewer_tab

    def current_viewer_tab(self, name, doc):
        if self.count():
            index = self.currentIndex()
            label = self.tabText(index)
            tab = self.tabs[label]
        else:
            tab = self.add_tab()
        tab.run_router('start', doc)
        return [tab.run_router], []


class ViewerTab(ConfigurableQObject):
    name_doc = Signal(str, dict)
    factories = List([FigureDispatcher], config=True)
    handler_registry = Dict(DottedObjectName(), config=True)

    def __init__(self, inner_tab_container, set_label, *args, **kwargs):
        self.update_config(load_config())
        self._inner_tab_container = inner_tab_container
        self._set_label = set_label
        self._run_start_uid = []
        self.run_router = QRunRouter(
            [factory(self._inner_tab_container.addTab)
             for factory in self.factories],
            handler_registry=self.handler_registry)
        super().__init__(*args, **kwargs)
        self.name_doc.connect(self.run_router)

    def rename(self, label):
        self._set_label(label)

    def __repr__(self):
        return f"<{type(self).__name__}>"

    def add_run(self, run, fill='delayed'):
        for name, doc in run.canonical(fill=fill):
            self.name_doc.emit(name, doc)

    def __call__(self, name, doc):
        self.name_doc.emit(name, doc)


class InnerTabContainer(QTabWidget):
    ...
