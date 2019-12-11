import tempfile

from bluesky import RunEngine
from ophyd.sim import det, motor
from bluesky.plans import scan
from bluesky_mpl.qt.viewer import start_viewers
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

viewers = start_viewers()
catalog.force_reload()
viewers.add_run(catalog[-1])
viewers.add_run(catalog[-2])
viewer = viewers.add_viewer('Another tab')
viewer.add_run(catalog[-3])
viewers['Another tab'].add_run(catalog[-4])
