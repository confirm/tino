'''Real-time collaboration via Yjs CRDT over WebSockets.

Each open file gets a YRoom backed by a pycrdt Doc. Multiple clients connect
to the same room and edits are merged via the Yjs sync protocol. When the
last client disconnects, the document is flushed to disk.
'''

import asyncio
import logging
from contextlib import asynccontextmanager
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

    def __init__(self, data_dir: Path, file_service: FileService, *,
                 auto_save: bool = True, room_ttl: int = 300):
        self.data_dir = data_dir
        self.file_service = file_service
        self._auto_save = auto_save
        self._room_ttl = room_ttl
        self._rooms: dict[tuple[str, str], YRoom] = {}
        self._room_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._ttl_tasks: dict[tuple[str, str], asyncio.Task] = {}

    def _get_lock(self, key: tuple[str, str]) -> asyncio.Lock:
        '''Return a per-room asyncio lock, creating it if needed.'''
        if key not in self._room_locks:
            self._room_locks[key] = asyncio.Lock()

        return self._room_locks[key]

    async def _get_or_create_room(self, slug: str, file_path: str) -> YRoom | None:
        '''Return an existing room, or create one by loading the file from disk.

        Returns None when the file does not exist on disk: without this guard,
        a client reconnecting to a deleted path would create an empty room,
        then flush empty content on disconnect, silently re-creating the file.
        '''
        key = (slug, file_path)
        lock = self._get_lock(key)
        async with lock:
            ttl_task = self._ttl_tasks.pop(key, None)
            if ttl_task:
                ttl_task.cancel()
                logger.info('Cancelled TTL for %s/%s (client reconnected)', slug, file_path)

            if key in self._rooms:
                return self._rooms[key]

            target = (self.data_dir / slug / file_path).resolve()
            if not target.is_file():
                return None

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

    @asynccontextmanager
    async def lock_path(self, slug: str, file_path: str):
        '''Hold the per-path lock and evict any existing room without flushing.

        Used by file delete/rename handlers to atomically tear down collab
        state and prevent the race where a pending flush re-creates the file
        the client just asked the server to remove.
        '''
        key = (slug, file_path)
        lock = self._get_lock(key)
        async with lock:
            ttl_task = self._ttl_tasks.pop(key, None)
            if ttl_task:
                ttl_task.cancel()
            room = self._rooms.pop(key, None)
            if room:
                try:
                    await room.stop()
                    logger.info('Evicted room for %s/%s', slug, file_path)
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception('Failed to stop room for %s/%s', slug, file_path)
            yield

        self._room_locks.pop(key, None)

    async def evict_under(self, slug: str, prefix: str) -> None:
        '''Evict every room whose path is under `prefix` (used for dir operations).'''
        match = [
            path for (s, path) in list(self._rooms.keys())
            if s == slug and (path == prefix or path.startswith(f'{prefix}/'))
        ]
        for path in match:
            async with self.lock_path(slug, path):
                pass

    async def _flush_room(self, slug: str, file_path: str, room: YRoom) -> None:
        '''Write the current Yjs document content to disk.'''
        ytext = room.ydoc.get('content', type=Text)
        self.file_service.write(slug, file_path, str(ytext))
        logger.info('Flushed %s/%s to disk', slug, file_path)

    async def _cleanup_room(self, slug: str, file_path: str) -> None:
        '''Schedule room teardown after the TTL expires.'''
        key = (slug, file_path)
        lock = self._get_lock(key)
        async with lock:
            room = self._rooms.get(key)
            if not room or len(room.clients) > 0:
                return
            self._ttl_tasks[key] = asyncio.create_task(
                self._deferred_cleanup(slug, file_path),
            )
            logger.info('Started %ds TTL for %s/%s', self._room_ttl, slug, file_path)

    async def _deferred_cleanup(self, slug: str, file_path: str) -> None:
        '''Wait for the TTL, then flush and stop the room.'''
        await asyncio.sleep(self._room_ttl)
        key = (slug, file_path)
        lock = self._get_lock(key)
        async with lock:
            self._ttl_tasks.pop(key, None)
            room = self._rooms.get(key)
            if not room or len(room.clients) > 0:
                return
            if self._auto_save:
                await self._flush_room(slug, file_path, room)
            await room.stop()
            del self._rooms[key]
            logger.info('Cleaned up room for %s/%s after TTL', slug, file_path)

        if key not in self._rooms:
            self._room_locks.pop(key, None)

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
        new_content = (result.get('content') or '') if result else ''
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

    def get_content(self, slug: str, file_path: str) -> str | None:
        '''Return the live YText content if a room exists, else None.'''
        room = self._rooms.get((slug, file_path))
        if room is None:
            return None
        ytext = room.ydoc.get('content', type=Text)
        return str(ytext)

    def start(self) -> None:
        '''Called on application startup (reserved for future use).'''

    async def shutdown(self) -> None:
        '''Cancel pending TTL tasks and flush all active rooms to disk.'''
        for task in self._ttl_tasks.values():
            task.cancel()
        self._ttl_tasks.clear()
        if not self._auto_save:
            return
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
        if not file_target.is_relative_to(bucket_path.resolve()):
            await websocket.close(code=4003, reason='Invalid path')
            return

        room = await self._get_or_create_room(slug, path)
        if room is None:
            await websocket.close(code=4404, reason='File not found')
            return

        await websocket.accept()

        channel = FastAPIChannel(websocket, f'{slug}/{path}')
        try:
            await room.serve(channel)
        except WebSocketDisconnect:
            pass
        finally:
            await self._cleanup_room(slug, path)
