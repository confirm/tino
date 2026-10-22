'''Tests for CollabManager: room lifecycle, eviction, reload and flushing.'''

import asyncio

import pytest
from pycrdt import Doc, Text

from tino.collab import CollabManager

pytestmark = pytest.mark.anyio


@pytest.fixture
def manager(data_dir, files):
    mgr = CollabManager(data_dir, files, room_ttl=0)
    yield mgr
    for task in list(mgr._room_tasks.values()):  # pylint: disable=protected-access
        task.cancel()


def _room_text(mgr, slug, path):
    return str(mgr._rooms[(slug, path)].ydoc.get('content', type=Text))  # pylint: disable=protected-access


async def test_room_loads_file_content(manager, files, bucket):
    files.write(bucket, 'a.typ', 'hello')
    room = await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    assert room is not None
    assert manager.get_content(bucket, 'a.typ') == 'hello'


async def test_room_is_reused(manager, files, bucket):
    files.write(bucket, 'a.typ', 'x')
    first = await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    second = await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    assert first is second


async def test_no_room_for_missing_file(manager, bucket, data_dir):
    assert await manager._get_or_create_room(bucket, 'ghost.typ') is None  # pylint: disable=protected-access
    assert not (data_dir / bucket / 'ghost.typ').exists()


async def test_get_content_without_room(manager, bucket):
    assert manager.get_content(bucket, 'a.typ') is None


async def test_reload_rooms_replaces_content(manager, files, bucket):
    files.write(bucket, 'a.typ', 'old 🦄 content')
    await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    files.write(bucket, 'a.typ', 'new')
    await manager.reload_rooms(bucket, ['a.typ', 'not-open.typ'])
    assert manager.get_content(bucket, 'a.typ') == 'new'


async def test_reload_to_empty_file(manager, files, bucket):
    files.write(bucket, 'a.typ', 'something')
    await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    files.write(bucket, 'a.typ', '')
    await manager.reload_rooms(bucket, ['a.typ'])
    assert manager.get_content(bucket, 'a.typ') == ''


@pytest.mark.parametrize('current, new', [
    ('', 'abc'),
    ('abc', ''),
    ('héllo 🦄 wörld', 'plain'),   # multi-byte: regression for byte vs. codepoint slicing
    ('plain', '🦄🦄🦄'),
])
async def test_replace_ytext(current, new):
    doc = Doc()
    ytext = doc.get('content', type=Text)
    ytext += current
    CollabManager._replace_ytext(ytext, current, new)  # pylint: disable=protected-access
    assert str(ytext) == new


async def test_lock_path_evicts_without_flush(manager, files, bucket):
    files.write(bucket, 'a.typ', 'disk')
    await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    manager._rooms[(bucket, 'a.typ')].ydoc.get('content', type=Text).insert(0, 'unsaved ')  # pylint: disable=protected-access

    async with manager.lock_path(bucket, 'a.typ'):
        assert manager.get_content(bucket, 'a.typ') is None

    assert files.read(bucket, 'a.typ')['content'] == 'disk'


async def test_evict_under_prefix(manager, files, bucket):
    for path in ('dir/a.typ', 'dir/sub/b.typ', 'dirx/c.typ', 'other.typ'):
        files.write(bucket, path, 'x')
        await manager._get_or_create_room(bucket, path)  # pylint: disable=protected-access

    await manager.evict_under(bucket, 'dir')

    assert sorted(p for _, p in manager._rooms) == ['dirx/c.typ', 'other.typ']  # pylint: disable=protected-access


async def test_deferred_cleanup_flushes_and_stops(manager, files, bucket):
    files.write(bucket, 'a.typ', 'disk')
    await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    manager._rooms[(bucket, 'a.typ')].ydoc.get('content', type=Text).insert(0, 'edited ')  # pylint: disable=protected-access

    await manager._cleanup_room(bucket, 'a.typ')  # pylint: disable=protected-access
    await asyncio.gather(*manager._ttl_tasks.values())  # pylint: disable=protected-access

    assert manager.get_content(bucket, 'a.typ') is None
    assert files.read(bucket, 'a.typ')['content'] == 'edited disk'


async def test_deferred_cleanup_respects_auto_save_off(data_dir, files, bucket):
    mgr = CollabManager(data_dir, files, auto_save=False, room_ttl=0)
    files.write(bucket, 'a.typ', 'disk')
    await mgr._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    mgr._rooms[(bucket, 'a.typ')].ydoc.get('content', type=Text).insert(0, 'edited ')  # pylint: disable=protected-access

    await mgr._cleanup_room(bucket, 'a.typ')  # pylint: disable=protected-access
    await asyncio.gather(*mgr._ttl_tasks.values())  # pylint: disable=protected-access

    assert files.read(bucket, 'a.typ')['content'] == 'disk'


async def test_reconnect_cancels_ttl(data_dir, files, bucket):
    mgr = CollabManager(data_dir, files, room_ttl=60)
    files.write(bucket, 'a.typ', 'x')
    room = await mgr._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    await mgr._cleanup_room(bucket, 'a.typ')  # pylint: disable=protected-access
    task = mgr._ttl_tasks[(bucket, 'a.typ')]  # pylint: disable=protected-access

    assert await mgr._get_or_create_room(bucket, 'a.typ') is room  # pylint: disable=protected-access
    await asyncio.sleep(0)
    assert task.cancelled()
    await mgr.shutdown()


async def test_shutdown_flushes_open_rooms(manager, files, bucket):
    files.write(bucket, 'a.typ', 'disk')
    await manager._get_or_create_room(bucket, 'a.typ')  # pylint: disable=protected-access
    manager._rooms[(bucket, 'a.typ')].ydoc.get('content', type=Text).insert(0, 'live ')  # pylint: disable=protected-access
    await manager.shutdown()
    assert files.read(bucket, 'a.typ')['content'] == 'live disk'
