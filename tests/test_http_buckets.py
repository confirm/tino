'''HTTP tests for bucket CRUD and the per-bucket role model.'''

import pytest

from tino import auth, config

from .conftest import ADMIN, COMMIT, EDITOR, NOBODY, VIEWER


# ── list ──

def test_list_shows_resolved_roles(login, acl_bucket, app_buckets):
    app_buckets.create('secret', access=[])
    for user, expected in [
        (ADMIN, {'proj': 'committer', 'secret': 'committer'}),
        (VIEWER, {'proj': 'viewer'}),
        (EDITOR, {'proj': 'editor'}),
        (COMMIT, {'proj': 'committer'}),
        (NOBODY, {}),
    ]:
        listed = login(user).get('/api/buckets').json()
        assert {b['slug']: b['role'] for b in listed} == expected, user.username


def test_list_uses_default_role_for_open_buckets(login, app_buckets, monkeypatch):
    monkeypatch.setattr(config, 'TINO_DEFAULT_ROLE', 'viewer')
    app_buckets.create('open')
    assert [b['role'] for b in login(NOBODY).get('/api/buckets').json()] == ['viewer']


def test_list_for_api_key(client, acl_bucket, app_buckets):  # pylint: disable=unused-argument
    app_buckets.create('other')
    raw, _ = auth.get_api_key_service().create('ci', {'proj': 'editor'})
    listed = client.get('/api/buckets', headers={'Authorization': f'Bearer {raw}'}).json()
    assert [(b['slug'], b['role']) for b in listed] == [('proj', 'editor')]


# ── get ──

def test_get_bucket(login, acl_bucket):
    data = login(VIEWER).get(f'/api/buckets/{acl_bucket}').json()
    assert data['slug'] == 'proj'
    assert data['description'] == 'Project'


def test_get_bucket_forbidden(login, acl_bucket):
    assert login(NOBODY).get(f'/api/buckets/{acl_bucket}').status_code == 403


def test_get_missing_bucket(admin_client):
    assert admin_client.get('/api/buckets/ghost').status_code == 404


# ── create ──

def test_create_bucket(admin_client, app_env):
    resp = admin_client.post('/api/buckets', json={
        'slug': 'new-one', 'name': 'New', 'description': 'd',
        'access': [{'group': 'g', 'role': 'editor'}], 'mcp_instructions': 'be nice',
    })
    assert resp.status_code == 201
    assert resp.json()['name'] == 'New'
    assert (app_env / 'new-one' / '.git').is_dir()


def test_create_commit_is_authored_by_user(admin_client, app_env):
    import git  # pylint: disable=import-outside-toplevel
    admin_client.post('/api/buckets', json={'slug': 'authored'})
    repo = git.Repo(app_env / 'authored')
    assert repo.head.commit.author.name == 'admin'
    repo.close()


def test_create_duplicate_is_409(admin_client, acl_bucket):
    assert admin_client.post('/api/buckets', json={'slug': acl_bucket}).status_code == 409


@pytest.mark.parametrize('slug', ['UPPER', 'with space', '-lead', 'trail-', 'a--b', '', 'x' * 51,
                                  '../evil'])
def test_create_rejects_invalid_slugs(admin_client, slug):
    assert admin_client.post('/api/buckets', json={'slug': slug}).status_code == 422


def test_create_requires_global_admin(login):
    resp = login(EDITOR).post('/api/buckets', json={'slug': 'nope'})
    assert resp.status_code == 403


# ── update ──

def test_update_bucket(admin_client, acl_bucket):
    resp = admin_client.put(f'/api/buckets/{acl_bucket}', json={'description': 'new'})
    assert resp.status_code == 200
    assert resp.json()['description'] == 'new'
    assert len(resp.json()['access']) == 3


def test_update_clears_name(admin_client, app_buckets):
    app_buckets.create('named', name='Name')
    assert admin_client.put('/api/buckets/named', json={'name': ''}).json()['name'] == ''


def test_update_missing_is_404(admin_client):
    assert admin_client.put('/api/buckets/ghost', json={}).status_code == 404


def test_update_requires_global_admin(login, acl_bucket):
    assert login(COMMIT).put(f'/api/buckets/{acl_bucket}', json={}).status_code == 403


# ── delete ──

def test_delete_bucket(admin_client, acl_bucket, app_env):
    assert admin_client.delete(f'/api/buckets/{acl_bucket}').status_code == 204
    assert not (app_env / acl_bucket).exists()
    assert admin_client.delete(f'/api/buckets/{acl_bucket}').status_code == 404


def test_delete_requires_global_admin(login, acl_bucket):
    assert login(COMMIT).delete(f'/api/buckets/{acl_bucket}').status_code == 403
