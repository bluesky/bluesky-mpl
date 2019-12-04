from qtpy.QtWidgets import QMainWindow, QApplication
assert QApplication.instance() is None
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
plt.ion()
from matplotlib.backends.backend_qt5 import _create_qApp
from bluesky import RunEngine
RE = RunEngine()
from ophyd.sim import det, motor
from bluesky.plans import scan

_create_qApp()
from bluesky_mpl.qt.viewer import Viewer
main_window = QMainWindow()
viewer = Viewer()
main_window.setCentralWidget(viewer)
main_window.show()

RE(scan([det], motor, -1, 1, 10), viewer)
