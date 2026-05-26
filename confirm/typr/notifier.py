'''Lightweight notification hub for broadcasting file-change events per bucket.'''

import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class BucketNotifier:
    '''Broadcasts simple JSON events to all clients subscribed to a bucket.'''

    def __init__(self):
        self._clients: dict[str, set[WebSocket]] = {}

    async def serve(self, websocket: WebSocket, slug: str):
        '''Accept a WebSocket and keep it open until the client disconnects.'''
        await websocket.accept()
        clients = self._clients.setdefault(slug, set())
        clients.add(websocket)

        try:
            while True:  # pylint: disable=while-used
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(websocket)

    async def notify(self, slug: str):
        '''Send a files-changed event to every client subscribed to the bucket.'''
        clients = self._clients.get(slug, set())
        dead = []

        for ws in clients:
            try:
                await ws.send_json({'type': 'files-changed'})
            except Exception:  # pylint: disable=broad-exception-caught
                dead.append(ws)

        for ws in dead:
            clients.discard(ws)
