'''Real-time collaboration via Yjs CRDT over WebSockets.

Each open file gets a YRoom backed by a pycrdt Doc. Multiple clients connect
to the same room and edits are merged via the Yjs sync protocol. When the
last client disconnects, the document is flushed to disk.
'''

import asyncio
import logging
from pathlib import Path

from anyio import Lock as AnyioLock
from fastapi import WebSocket, WebSocketDisconnect
from pycrdt import Channel, Doc, Text
from pycrdt.websocket import YRoom

from .services.file import FileService

logger = logging.getLogger(__name__)


class FastAPIChannel(Channel):
    '''Adapts a FastAPI WebSocket to the pycrdt Channel interface.'''

    def __init__(self, websocket: WebSocket, path: str):
        self._websocket = websocket
        self._path = path
        self._send_lock = AnyioLock()

    @property
    def path(self) -> str:
        return self._path

    async def send(self, message: bytes):
        '''Send a binary message to the client, serialized with a lock.'''
        async with self._send_lock:
            await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        '''Receive a binary message from the client.'''
        return bytes(await self._websocket.receive_bytes())

    async def __anext__(self) -> bytes:
        try:
            return await self.recv()
        except Exception as exc:
            raise StopAsyncIteration() from exc


class CollabManager:
    '''Manages Yjs collaboration rooms for concurrent file editing.

    Rooms are created lazily when the first client connects to a file and
    torn down (with a disk flush) when the last client disconnects.
    '''

    def __init__(self, data_dir: Path, file_service: FileService):
        self.data_dir = data_dir
        self.file_service = file_service
        self._rooms: dict[tuple[str, str], YRoom] = {}
        self._room_locks: dict[tuple[str, str], asyncio.Lock] = {}

    def _get_lock(self, key: tuple[str, str]) -> asyncio.Lock:
        '''Return a per-room asyncio lock, creating it if needed.'''
        if key not in self._room_locks:
            self._room_locks[key] = asyncio.Lock()

        return self._room_locks[key]

    async def _get_or_create_room(self, slug: str, file_path: str) -> YRoom:
        '''Return an existing room or create one by loading the file from disk.'''
        key = (slug, file_path)
        lock = self._get_lock(key)
        async with lock:
            if key in self._rooms:
                return self._rooms[key]

            ydoc = Doc()
            ytext = ydoc.get('content', type=Text)

            result = self.file_service.read(slug, file_path)
            if result:
                ytext += result['content']

            room = YRoom(ydoc=ydoc)
            asyncio.create_task(room.start())
            await room.started.wait()
            self._rooms[key] = room
            logger.info('Created room for %s/%s', slug, file_path)
            return room

    async def _flush_room(self, slug: str, file_path: str, room: YRoom) -> None:
        '''Write the current Yjs document content to disk.'''
        ytext = room.ydoc.get('content', type=Text)
        self.file_service.write(slug, file_path, str(ytext))
        logger.info('Flushed %s/%s to disk', slug, file_path)

    async def _cleanup_room(self, slug: str, file_path: str) -> None:
        '''Flush and stop a room if no clients remain connected.'''
        key = (slug, file_path)
        lock = self._get_lock(key)
        async with lock:
            room = self._rooms.get(key)
            if room and len(room.clients) == 0:
                await self._flush_room(slug, file_path, room)
                await room.stop()
                del self._rooms[key]
                logger.info('Cleaned up room for %s/%s', slug, file_path)

    async def reload_rooms(self, slug: str, paths: list[str]) -> None:
        '''Reload room content from disk after external file changes.

        Called after git restore or other operations that change files on disk
        outside the CRDT. Connected clients receive the update via sync.
        '''
        for path in paths:
            key = (slug, path)
            lock = self._get_lock(key)
            async with lock:
                room = self._rooms.get(key)
                if room:
                    self._sync_room_to_disk(room, slug, path)

    def _sync_room_to_disk(self, room, slug, path):
        '''Replace the room's YText with the current content on disk.'''
        result = self.file_service.read(slug, path)
        new_content = result['content'] if result else ''
        ytext = room.ydoc.get('content', type=Text)
        current = str(ytext)
        if current != new_content:
            CollabManager._replace_ytext(ytext, current, new_content)
            logger.info('Reloaded room for %s/%s', slug, path)

    @staticmethod
    def _replace_ytext(ytext, current, new_content):
        '''Clear existing YText and insert new content.'''
        if current:
            del ytext[0:len(current)]
        if new_content:
            ytext += new_content

    def start(self) -> None:
        '''Called on application startup (reserved for future use).'''

    async def shutdown(self) -> None:
        '''Flush all active rooms to disk. Called on application shutdown.'''
        for (slug, file_path), room in list(self._rooms.items()):
            try:
                await self._flush_room(slug, file_path, room)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception('Flush failed for %s/%s', slug, file_path)

    async def serve(self, websocket: WebSocket, slug: str, path: str) -> None:
        '''Handle a WebSocket connection for collaborative editing of a file.'''
        bucket_path = self.data_dir / slug
        if not bucket_path.is_dir():
            await websocket.close(code=4004, reason='Bucket not found')
            return

        file_target = (bucket_path / path).resolve()
        if not str(file_target).startswith(str(bucket_path.resolve())):
            await websocket.close(code=4003, reason='Invalid path')
            return

        room = await self._get_or_create_room(slug, path)
        await websocket.accept()

        channel = FastAPIChannel(websocket, f'{slug}/{path}')
        try:
            await room.serve(channel)
        except WebSocketDisconnect:
            pass
        finally:
            await self._cleanup_room(slug, path)
