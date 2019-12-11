from bluesky import RunEngine
from ophyd.sim import det, motor
from bluesky.plans import scan
from bluesky_mpl.qt.viewer import start_viewers

RE = RunEngine()
viewers = start_viewers()
RE.subscribe(viewers)

RE(scan([det], motor, -1, 1, 10))
RE(scan([det], motor, -3, 3, 5))
