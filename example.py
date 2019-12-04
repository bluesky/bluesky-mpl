from bluesky import RunEngine
RE = RunEngine()
from ophyd.sim import det, motor
from bluesky.plans import scan

from bluesky_mpl.qt.viewer import start_viewer
viewer = start_viewer()
RE.subscribe(viewer)

RE(scan([det], motor, -1, 1, 10))
