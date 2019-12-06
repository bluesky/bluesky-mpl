import tempfile

from bluesky import RunEngine
from ophyd.sim import det, motor
from bluesky.plans import scan
from bluesky_mpl.qt.viewer import start_viewer
from suitcase.msgpack import Serializer
from event_model import RunRouter
from databroker._drivers.msgpack import BlueskyMsgpackCatalog

RE = RunEngine()
directory = tempfile.TemporaryDirectory().name

catalog = BlueskyMsgpackCatalog(f'{directory}/*.msgpack')


def factory(name, doc):
    serializer = Serializer(directory)
    serializer(name, doc)
    return [serializer], []


rr = RunRouter([factory])

RE.subscribe(rr)

uid, = RE(scan([det], motor, -1, 1, 10))
uid, = RE(scan([det], motor, -1, 1, 5))
uid, = RE(scan([det], motor, -1, 1, 5))
uid, = RE(scan([det], motor, -3, 3, 5))

viewer = start_viewer()
catalog.force_reload()
viewer.add_run(catalog[-1])
viewer.add_run(catalog[-2])
tab = viewer.add_tab('Another tab')
tab.add_run(catalog[-3])
viewer.tabs['Another tab'].add_run(catalog[-4])
