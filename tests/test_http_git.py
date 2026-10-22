'''HTTP tests for the git endpoints.'''

import pytest

from tino import dependencies

from .conftest import COMMIT, EDITOR, NOBODY, VIEWER

BASE = '/api/buckets/proj/git'


@pytest.fixture
def repo(acl_bucket):  # pylint: disable=unused-argument
    '''Seed ``proj`` with two commits of ``a.typ``; returns their SHAs (oldest first).'''
    files = dependencies.get_file_service()
    git = dependencies.get_git_service()
    files.write('proj', 'a.typ', 'v1\n')
    first = git.commit('proj', ['a.typ'], 'first').sha
    files.write('proj', 'a.typ', 'v2\n')
    files.upload('proj', 'img.png', b'\x89PNG')
    second = git.commit('proj', ['a.typ', 'img.png'], 'second').sha
    return first, second


def test_status(login, repo):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'new.typ', 'x')
    assert login(VIEWER).get(f'{BASE}/status').json() == [
        {'path': 'new.typ', 'status': 'untracked'},
    ]


def test_log(login, repo):
    log = login(VIEWER).get(f'{BASE}/log').json()
    assert [c['sha'] for c in log] == list(reversed(repo))


def test_log_max_count_validation(login, repo):  # pylint: disable=unused-argument
    client = login(VIEWER)
    assert len(client.get(f'{BASE}/log', params={'max_count': 1}).json()) == 1
    assert client.get(f'{BASE}/log', params={'max_count': 0}).status_code == 422
    assert client.get(f'{BASE}/log', params={'max_count': 501}).status_code == 422


def test_diff_of_commit(login, repo):
    [entry] = login(VIEWER).get(f'{BASE}/diff', params={'ref': repo[1], 'path': 'a.typ'}).json()
    assert '+v2' in entry['diff']


def test_diff_working_tree(login, repo):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'a.typ', 'v3\n')
    [entry] = login(VIEWER).get(f'{BASE}/diff').json()
    assert '+v3' in entry['diff']


def test_tree_and_changed(login, repo):
    client = login(VIEWER)
    assert client.get(f'{BASE}/tree/{repo[0]}').json() == ['a.typ']
    assert client.get(f'{BASE}/changed/{repo[1]}').json() == ['a.typ', 'img.png']


@pytest.mark.parametrize('endpoint', ['tree', 'changed'])
def test_unknown_ref_is_404(login, repo, endpoint):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/{endpoint}/deadbeef').status_code == 404


def test_unknown_diff_ref_is_404(login, repo):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/diff', params={'ref': 'deadbeef'}).status_code == 404


def test_show(login, repo):
    data = login(VIEWER).get(f'{BASE}/show/{repo[0]}/content/a.typ').json()
    assert data == {'ref': repo[0], 'path': 'a.typ', 'content': 'v1\n', 'binary': False}


def test_show_raw(login, repo):
    resp = login(VIEWER).get(f'{BASE}/show/{repo[1]}/raw/img.png')
    assert resp.content == b'\x89PNG'
    assert resp.headers['content-type'] == 'image/png'


def test_show_raw_missing(login, repo):
    assert login(VIEWER).get(f'{BASE}/show/{repo[0]}/raw/img.png').status_code == 404


@pytest.mark.parametrize('kind', ['content', 'raw'])
def test_show_unknown_ref_is_404(login, repo, kind):  # pylint: disable=unused-argument
    assert login(VIEWER).get(f'{BASE}/show/deadbeef/{kind}/a.typ').status_code == 404


def test_restore_unknown_ref_is_404(login, repo):  # pylint: disable=unused-argument
    resp = login(EDITOR).post(f'{BASE}/restore', json={'ref': 'deadbeef', 'paths': ['a.typ']})
    assert resp.status_code == 404


# ── commit ──

def test_commit_requires_committer(login, repo):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'b.typ', 'x')
    body = {'files': ['b.typ'], 'message': 'add b'}
    assert login(EDITOR).post(f'{BASE}/commit', json=body).status_code == 403

    resp = login(COMMIT).post(f'{BASE}/commit', json=body)
    assert resp.status_code == 200
    assert resp.json()['message'] == 'add b'
    assert 'co' in resp.json()['author']


def test_commit_without_files_is_400(login, repo):  # pylint: disable=unused-argument
    resp = login(COMMIT).post(f'{BASE}/commit', json={'files': [], 'message': 'm'})
    assert resp.status_code == 400


# ── restore ──

def test_restore(login, repo):
    client = login(EDITOR)
    resp = client.post(f'{BASE}/restore', json={'ref': repo[0], 'paths': ['a.typ']})
    assert resp.json() == {'restored': ['a.typ']}
    assert dependencies.get_file_service().read('proj', 'a.typ')['content'] == 'v1\n'


def test_restore_nothing_is_404(login, repo):
    resp = login(EDITOR).post(f'{BASE}/restore', json={'ref': repo[0], 'paths': ['ghost']})
    assert resp.status_code == 404


def test_restore_requires_editor(login, repo):
    resp = login(VIEWER).post(f'{BASE}/restore', json={'ref': repo[0], 'paths': ['a.typ']})
    assert resp.status_code == 403


def test_outsider_has_no_git_access(login, repo):  # pylint: disable=unused-argument
    client = login(NOBODY)
    for path in ('status', 'log', 'diff'):
        assert client.get(f'{BASE}/{path}').status_code == 403
