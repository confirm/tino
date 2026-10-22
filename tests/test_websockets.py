'''Tests for the WebSocket endpoints (events + collab) and the BucketNotifier.'''

import pytest
from starlette.websockets import WebSocketDisconnect

from tino import auth, dependencies
from tino.notifier import BucketNotifier

from .conftest import EDITOR, NOBODY, VIEWER


def _close_code(client, url):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(url) as ws:
            ws.receive_text()
    return exc.value.code


# ── /events ──

def test_events_requires_session(client, acl_bucket):  # pylint: disable=unused-argument
    assert _close_code(client, '/api/buckets/proj/events') == 4401


def test_events_missing_bucket(login):
    assert _close_code(login(VIEWER), '/api/buckets/ghost/events') == 4004


def test_events_forbidden(login, acl_bucket):  # pylint: disable=unused-argument
    assert _close_code(login(NOBODY), '/api/buckets/proj/events') == 4403


def test_events_receive_file_change(login, acl_bucket):  # pylint: disable=unused-argument
    viewer = login(VIEWER)
    with viewer.websocket_connect('/api/buckets/proj/events') as ws:
        ws.send_text('ping')  # ensure the server registered the socket
        raw, _ = auth.get_api_key_service().create('editor', {'proj': 'editor'})
        resp = viewer.post('/api/buckets/proj/files', json={'path': 'n.typ'},
                           headers={'Authorization': f'Bearer {raw}'})
        assert resp.status_code == 201
        assert ws.receive_json() == {'type': 'files-changed'}


# ── /collab ──

def test_collab_requires_session(client, acl_bucket):  # pylint: disable=unused-argument
    assert _close_code(client, '/api/buckets/proj/collab/a.typ') == 4401


def test_collab_missing_bucket(login):
    assert _close_code(login(EDITOR), '/api/buckets/ghost/collab/a.typ') == 4004


def test_collab_requires_editor(login, acl_bucket):  # pylint: disable=unused-argument
    assert _close_code(login(VIEWER), '/api/buckets/proj/collab/a.typ') == 4403


def test_collab_missing_file(login, acl_bucket):  # pylint: disable=unused-argument
    assert _close_code(login(EDITOR), '/api/buckets/proj/collab/ghost.typ') == 4404


def test_collab_rejects_traversal(login, acl_bucket):  # pylint: disable=unused-argument
    assert _close_code(login(EDITOR), '/api/buckets/proj/collab/..%2F..%2Fx') == 4003


def test_collab_connects_and_syncs(login, acl_bucket):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'a.typ', 'hello')
    with login(EDITOR).websocket_connect('/api/buckets/proj/collab/a.typ') as ws:
        # The room greets every client with a Yjs sync step 1 message.
        message = ws.receive_bytes()
        assert message[:2] == b'\x00\x00'
        assert dependencies.get_collab_manager().get_content('proj', 'a.typ') == 'hello'


# ── BucketNotifier ──

class _FakeSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    async def send_json(self, data):
        if self.fail:
            raise RuntimeError('closed')
        self.sent.append(data)


@pytest.mark.anyio
async def test_notifier_broadcasts_and_prunes_dead_clients():
    notifier = BucketNotifier()
    alive, dead, other = _FakeSocket(), _FakeSocket(fail=True), _FakeSocket()
    notifier._clients = {'a': {alive, dead}, 'b': {other}}  # pylint: disable=protected-access

    await notifier.notify('a')

    assert alive.sent == [{'type': 'files-changed'}]
    assert other.sent == []
    assert notifier._clients['a'] == {alive}  # pylint: disable=protected-access


@pytest.mark.anyio
async def test_notifier_unknown_bucket_is_noop():
    await BucketNotifier().notify('ghost')
