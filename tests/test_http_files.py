'''HTTP tests for the file endpoints, including role enforcement and path safety.'''

import io
import zipfile

import pytest

from tino import dependencies

from .conftest import EDITOR, NOBODY, VIEWER

BASE = '/api/buckets/proj/files'


@pytest.fixture
def editor(login, acl_bucket):  # pylint: disable=unused-argument
    return login(EDITOR)


@pytest.fixture
def seeded(acl_bucket):  # pylint: disable=unused-argument
    svc = dependencies.get_file_service()
    svc.write('proj', 'main.typ', '= Hello')
    svc.write('proj', 'sub/part.typ', 'part')
    svc.upload('proj', 'img.png', b'\x89PNG\r\n')
    return svc


# ── read ──

def test_list_files(login, seeded):  # pylint: disable=unused-argument
    paths = [e['path'] for e in login(VIEWER).get(BASE).json()]
    assert paths == ['img.png', 'main.typ', 'sub', 'sub/part.typ']


def test_read_file(login, seeded):  # pylint: disable=unused-argument
    data = login(VIEWER).get(f'{BASE}/main.typ').json()
    assert data['path'] == 'main.typ'
    assert data['content'] == '= Hello'
    assert 'modified' in data


def test_read_nested_file(login, seeded):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/sub/part.typ').json()['content'] == 'part'


def test_read_binary_file_is_flagged(login, seeded):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/img.png').json()['binary'] is True


def test_read_missing_file(login, seeded):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/ghost.typ').status_code == 404


def test_raw_file(login, seeded):  # pylint: disable=unused-argument
    resp = login(VIEWER).get(f'{BASE}/raw/img.png')
    assert resp.content == b'\x89PNG\r\n'
    assert resp.headers['content-type'] == 'image/png'


def test_raw_missing(login, seeded):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/raw/ghost.png').status_code == 404


@pytest.mark.parametrize('path', ['..%2F..%2Fapi_keys.yml', '%2Fetc%2Fpasswd'])
def test_raw_rejects_traversal(login, seeded, path):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/raw/{path}').status_code == 404


def test_download_zip(login, seeded):  # pylint: disable=unused-argument
    resp = login(VIEWER).get(f'{BASE}/download')
    assert resp.status_code == 200
    assert 'proj.zip' in resp.headers['content-disposition']
    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert sorted(names) == ['img.png', 'main.typ', 'sub/part.typ']


def test_outsider_cannot_read(login, seeded):  # pylint: disable=unused-argument
    client = login(NOBODY)
    assert client.get(BASE).status_code == 403
    assert client.get(f'{BASE}/main.typ').status_code == 403
    assert client.get(f'{BASE}/raw/img.png').status_code == 403
    assert client.get(f'{BASE}/download').status_code == 403


def test_missing_bucket_is_404(admin_client):
    assert admin_client.get('/api/buckets/ghost/files').status_code == 404


# ── write: role enforcement ──

@pytest.mark.parametrize('method, url, kwargs', [
    ('post', BASE, {'json': {'path': 'x.typ'}}),
    ('put', f'{BASE}/main.typ', {'json': {'content': 'x'}}),
    ('delete', f'{BASE}/main.typ', {}),
    ('delete', f'{BASE}/dir/sub', {}),
    ('post', f'{BASE}/mkdir', {'json': {'path': 'd'}}),
    ('post', f'{BASE}/rename', {'json': {'old_path': 'main.typ', 'new_path': 'x.typ'}}),
    ('post', f'{BASE}/rename-dir', {'json': {'old_path': 'sub', 'new_path': 'x'}}),
    ('post', f'{BASE}/upload', {'files': {'files': ('a.txt', b'x')}}),
])
def test_viewer_cannot_write(login, seeded, method, url, kwargs):
    resp = getattr(login(VIEWER), method)(url, **kwargs)
    assert resp.status_code == 403
    assert seeded.read('proj', 'main.typ')['content'] == '= Hello'


# ── write ──

def test_create_file(editor):
    resp = editor.post(BASE, json={'path': 'new.typ', 'content': 'hi'})
    assert resp.status_code == 201
    assert editor.get(f'{BASE}/new.typ').json()['content'] == 'hi'


def test_create_existing_is_409(editor, seeded):  # pylint: disable=unused-argument
    assert editor.post(BASE, json={'path': 'main.typ'}).status_code == 409


def test_create_traversal_is_409(editor, app_env):
    assert editor.post(BASE, json={'path': '../escape.typ'}).status_code == 409
    assert not (app_env / 'escape.typ').exists()


def test_save_file(editor, seeded):  # pylint: disable=unused-argument
    resp = editor.put(f'{BASE}/main.typ', json={'content': 'updated'})
    assert resp.status_code == 200
    assert resp.json()['modified']
    assert editor.get(f'{BASE}/main.typ').json()['content'] == 'updated'


def test_save_traversal_is_400(editor, app_env):
    assert editor.put(f'{BASE}/..%2Fescape.typ', json={'content': 'x'}).status_code == 400
    assert not (app_env / 'escape.typ').exists()


def test_delete_file(editor, seeded):  # pylint: disable=unused-argument
    assert editor.delete(f'{BASE}/main.typ').status_code == 204
    assert editor.delete(f'{BASE}/main.typ').status_code == 404


def test_mkdir(editor):
    assert editor.post(f'{BASE}/mkdir', json={'path': 'a/b'}).status_code == 201
    assert editor.post(f'{BASE}/mkdir', json={'path': 'a/b'}).status_code == 409
    assert {'path': 'a/b', 'type': 'directory'} in editor.get(BASE).json()


def test_rename_file(editor, seeded):  # pylint: disable=unused-argument
    resp = editor.post(f'{BASE}/rename', json={'old_path': 'main.typ', 'new_path': 'x/y.typ'})
    assert resp.status_code == 200
    assert editor.get(f'{BASE}/x/y.typ').json()['content'] == '= Hello'


def test_rename_onto_existing_is_400(editor, seeded):  # pylint: disable=unused-argument
    resp = editor.post(f'{BASE}/rename', json={'old_path': 'main.typ', 'new_path': 'img.png'})
    assert resp.status_code == 400


def test_rename_dir(editor, seeded):  # pylint: disable=unused-argument
    resp = editor.post(f'{BASE}/rename-dir', json={'old_path': 'sub', 'new_path': 'moved'})
    assert resp.json() == {'affected': ['sub/part.typ']}
    assert editor.get(f'{BASE}/moved/part.typ').status_code == 200


def test_rename_dir_missing_is_400(editor):
    resp = editor.post(f'{BASE}/rename-dir', json={'old_path': 'ghost', 'new_path': 'x'})
    assert resp.status_code == 400


def test_delete_dir(editor, seeded):  # pylint: disable=unused-argument
    assert editor.delete(f'{BASE}/dir/sub').status_code == 204
    assert editor.delete(f'{BASE}/dir/sub').status_code == 404


def test_upload_files_with_prefix(editor):
    resp = editor.post(f'{BASE}/upload', params={'prefix': 'assets'}, files=[
        ('files', ('a.png', b'A')), ('files', ('b.txt', b'B')),
    ])
    assert resp.status_code == 201
    assert resp.json() == {'uploaded': ['assets/a.png', 'assets/b.txt']}


def test_upload_zip_is_extracted(editor):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('doc/main.typ', 'zipped')
        zf.writestr('../evil.txt', 'pwned')
    resp = editor.post(f'{BASE}/upload', files={'files': ('bundle.ZIP', buf.getvalue())})
    assert resp.json() == {'uploaded': ['doc/main.typ']}
    assert editor.get(f'{BASE}/doc/main.typ').json()['content'] == 'zipped'


def test_upload_traversal_is_400(editor, app_env):
    resp = editor.post(f'{BASE}/upload', params={'prefix': '..'},
                       files={'files': ('evil.txt', b'x')})
    assert resp.status_code == 400
    assert not (app_env / 'evil.txt').exists()
