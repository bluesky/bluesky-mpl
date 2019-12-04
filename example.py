from bluesky import RunEngine
from ophyd.sim import det, motor
from bluesky.plans import scan
from bluesky_mpl.qt.viewer import start_viewer

RE = RunEngine()
viewer = start_viewer()
RE.subscribe(viewer)

RE(scan([det], motor, -1, 1, 10))
