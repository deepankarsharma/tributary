from json import loads as load_json
from websocket import create_connection
from ..base import _wrap, StreamNone, StreamEnd
from ..thread import run


def WebSocket(url, *args, **kwargs):
    return SyncWebSocket(url, *args, **kwargs)


def SyncWebSocket(url, json=False, wrap=False):
    def _listen(url):
        ws = create_connection(url)
        for x in run(ws.recv):
            if isinstance(x, StreamNone):
                continue
            elif not x or isinstance(x, StreamEnd):
                break

            if json:
                x = load_json(x)
            if wrap:
                x = [x]
            yield x

    return _wrap(_listen, dict(url=url), name='WebSocket')
