import json

import git
import pytest
from fastapi.testclient import TestClient

from tino import config
from tino.app import create_app
from tino.dependencies import get_bucket_service, get_collab_manager, get_compiler_service, \
    get_file_service, get_font_service, get_git_service, get_search_service, \
    get_review_service, get_template_service


@pytest.fixture(autouse=True)
def app_config(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    bucket_dir = data_dir / 'buckets'
    package_dir = data_dir / 'packages'
    font_dir = data_dir / 'fonts'
    for path in (data_dir, bucket_dir, package_dir, font_dir):
        path.mkdir(parents=True)

    monkeypatch.setattr(config, 'TINO_AUTH_DISABLED', True)
    monkeypatch.setattr(config, 'TINO_BASE_URL', 'http://localhost:8000')
    monkeypatch.setattr(config, 'TINO_DATA_DIR', data_dir)
    monkeypatch.setattr(config, 'TINO_BUCKET_DIR', bucket_dir)
    monkeypatch.setattr(config, 'TINO_PACKAGE_DIR', package_dir)
    monkeypatch.setattr(config, 'TINO_FONT_DIR', font_dir)

    for factory in (
        get_bucket_service,
        get_collab_manager,
        get_compiler_service,
        get_file_service,
        get_font_service,
        get_git_service,
        get_review_service,
        get_search_service,
        get_template_service,
    ):
        factory.cache_clear()

    yield bucket_dir

    for factory in (
        get_bucket_service,
        get_collab_manager,
        get_compiler_service,
        get_file_service,
        get_font_service,
        get_git_service,
        get_review_service,
        get_search_service,
        get_template_service,
    ):
        factory.cache_clear()


@pytest.fixture
def client(app_config):
    app = create_app()
    return TestClient(app)


def create_bucket_with_file(client, slug='paper', path='main.typ'):
    response = client.post('/api/buckets', json={'slug': slug, 'name': 'Paper'})
    assert response.status_code == 201

    response = client.post(
        f'/api/buckets/{slug}/files',
        json={'path': path, 'content': 'Hello world\nSecond line\n'},
    )
    assert response.status_code == 201


def comment_payload(path='main.typ'):
    return {
        'anchor': {
            'column': 1,
            'end_column': 6,
            'end_line': 1,
            'from_offset': 0,
            'line': 1,
            'quote': 'Hello',
            'to_offset': 5,
        },
        'body': 'Clarify this opening.',
        'path': path,
    }


def test_comment_thread_lifecycle(client, app_config):
    create_bucket_with_file(client)

    response = client.post('/api/buckets/paper/comments', json=comment_payload())

    assert response.status_code == 201
    created = response.json()
    thread_id = created['id']
    assert created['path'] == 'main.typ'
    assert created['anchor']['quote'] == 'Hello'
    assert created['status'] == 'open'
    assert created['created_by'] == 'tino'
    assert created['messages'][0]['body'] == 'Clarify this opening.'

    response = client.get('/api/buckets/paper/comments?path=main.typ')

    assert response.status_code == 200
    threads = response.json()
    assert [thread['id'] for thread in threads] == [thread_id]

    response = client.post(
        f'/api/buckets/paper/comments/{thread_id}/replies',
        json={'body': 'Agreed; this needs context.'},
    )

    assert response.status_code == 200
    replied = response.json()
    assert [message['body'] for message in replied['messages']] == [
        'Clarify this opening.',
        'Agreed; this needs context.',
    ]

    response = client.patch(
        f'/api/buckets/paper/comments/{thread_id}',
        json={'status': 'resolved'},
    )

    assert response.status_code == 200
    resolved = response.json()
    assert resolved['status'] == 'resolved'
    assert resolved['resolved_by'] == 'tino'
    assert resolved['resolved_at']

    response = client.get('/api/buckets/paper/comments?path=main.typ')

    assert response.status_code == 200
    assert response.json() == []

    response = client.get('/api/buckets/paper/comments?path=main.typ&status=all')

    assert response.status_code == 200
    assert response.json()[0]['id'] == thread_id

    store = app_config / 'paper' / '.tino' / 'comments.json'
    data = json.loads(store.read_text())
    assert data['version'] == 1
    assert data['threads'][0]['id'] == thread_id

    repo = git.Repo(app_config / 'paper')
    tracked = repo.git.ls_tree('-r', '--name-only', 'HEAD').splitlines()
    assert '.tino/comments.json' in tracked
    assert 'Tino-Meta: true' in repo.head.commit.message


def test_comment_rejects_invalid_anchor_path(client):
    create_bucket_with_file(client)

    payload = comment_payload('../secret.typ')
    response = client.post('/api/buckets/paper/comments', json=payload)

    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid comment path'
