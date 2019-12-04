import functools

import event_model
from traitlets.traitlets import Dict, DottedObjectName, List
from qtpy.QtWidgets import QWidget, QVBoxLayout
from qtpy.QtCore import QObject, Signal

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
