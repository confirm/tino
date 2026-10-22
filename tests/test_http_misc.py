'''HTTP tests for search, API keys, fonts, compile, templates and misc endpoints.'''

import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from tino import auth, config, dependencies
from tino.routers import search as search_router
from tino.services import template as template_module

from .conftest import EDITOR, NOBODY, VIEWER

# ── search ──


@pytest.fixture
def searchable(acl_bucket, app_buckets):  # pylint: disable=unused-argument
    files = dependencies.get_file_service()
    app_buckets.create('secret')
    files.write('proj', 'notes.typ', 'the needle is here')
    files.write('secret', 'hidden.typ', 'needle')


def test_search_respects_access(login, searchable):  # pylint: disable=unused-argument
    results = login(VIEWER).get('/api/search', params={'q': 'needle'}).json()
    assert [(r['bucket'], r['path']) for r in results] == [('proj', 'notes.typ')]
    assert results[0]['snippets'][0]['line'] == 1


def test_search_admin_sees_all(admin_client, searchable):  # pylint: disable=unused-argument
    results = admin_client.get('/api/search', params={'q': 'needle'}).json()
    assert {r['bucket'] for r in results} == {'proj', 'secret'}


def test_search_short_query_is_empty(admin_client, searchable):  # pylint: disable=unused-argument
    assert admin_client.get('/api/search', params={'q': ' n '}).json() == []


def test_search_single_bucket(admin_client, searchable):  # pylint: disable=unused-argument
    results = admin_client.get('/api/search', params={'q': 'needle', 'bucket': 'secret'}).json()
    assert [r['bucket'] for r in results] == ['secret']


def test_search_single_bucket_forbidden(login, searchable):  # pylint: disable=unused-argument
    resp = login(VIEWER).get('/api/search', params={'q': 'needle', 'bucket': 'secret'})
    assert resp.status_code == 403


def test_search_single_bucket_missing(admin_client):
    resp = admin_client.get('/api/search', params={'q': 'needle', 'bucket': 'ghost'})
    assert resp.status_code == 404


def test_search_caps_results(admin_client, acl_bucket, monkeypatch):  # pylint: disable=unused-argument
    monkeypatch.setattr(search_router, 'MAX_RESULTS', 2)
    files = dependencies.get_file_service()
    for i in range(5):
        files.write('proj', f'doc{i}.typ', 'x')
    assert len(admin_client.get('/api/search', params={'q': 'doc'}).json()) == 2


# ── API keys ──

def test_api_key_lifecycle(admin_client):
    created = admin_client.post('/api/keys', json={'label': 'CI', 'access': {'proj': 'viewer'}})
    assert created.status_code == 201
    token, key_id = created.json()['token'], created.json()['id']
    assert token.startswith('tino_')

    listed = admin_client.get('/api/keys').json()
    assert [k['id'] for k in listed] == [key_id]
    assert 'token' not in listed[0]

    patched = admin_client.patch(f'/api/keys/{key_id}', json={'label': 'CD', 'access': {}})
    assert patched.json()['label'] == 'CD'

    assert admin_client.delete(f'/api/keys/{key_id}').status_code == 204
    assert admin_client.delete(f'/api/keys/{key_id}').status_code == 404
    assert admin_client.patch(f'/api/keys/{key_id}', json={'label': 'x'}).status_code == 404


def test_api_keys_require_admin(login):
    client = login(EDITOR)
    assert client.get('/api/keys').status_code == 403
    assert client.post('/api/keys', json={'label': 'x'}).status_code == 403


def test_api_key_cannot_manage_keys(client):
    raw, _ = auth.get_api_key_service().create('ci', {})
    assert client.get('/api/keys', headers={'Authorization': f'Bearer {raw}'}).status_code == 403


def test_api_key_grants_bucket_access(client, acl_bucket):  # pylint: disable=unused-argument
    raw, _ = auth.get_api_key_service().create('ci', {'proj': 'editor'})
    headers = {'Authorization': f'Bearer {raw}'}
    resp = client.post('/api/buckets/proj/files', json={'path': 'k.typ'}, headers=headers)
    assert resp.status_code == 201
    assert client.post('/api/buckets/proj/git/commit', headers=headers,
                       json={'files': ['k.typ'], 'message': 'm'}).status_code == 403


def test_revoked_api_key_is_rejected(client, acl_bucket):  # pylint: disable=unused-argument
    svc = auth.get_api_key_service()
    raw, rec = svc.create('ci', {'proj': 'viewer'})
    headers = {'Authorization': f'Bearer {raw}'}
    assert client.get('/api/buckets/proj', headers=headers).status_code == 200
    svc.revoke(rec['id'])
    assert client.get('/api/buckets/proj', headers=headers).status_code == 401


# ── fonts ──

def test_font_lifecycle(admin_client, app_env):  # pylint: disable=unused-argument
    resp = admin_client.post('/api/fonts/upload', files=[
        ('files', ('A.ttf', b'12')), ('files', ('b.woff2', b'1')),
    ])
    assert resp.json() == {'uploaded': ['A.ttf', 'b.woff2']}
    assert admin_client.get('/api/fonts').json() == [
        {'filename': 'A.ttf', 'size': 2}, {'filename': 'b.woff2', 'size': 1},
    ]
    assert admin_client.delete('/api/fonts/A.ttf').status_code == 204
    assert admin_client.delete('/api/fonts/A.ttf').status_code == 404


def test_font_upload_rejects_invalid(admin_client):
    resp = admin_client.post('/api/fonts/upload', files={'files': ('evil.sh', b'x')})
    assert resp.status_code == 400


def test_fonts_require_admin(login):
    assert login(EDITOR).get('/api/fonts').status_code == 403


# ── compile (typst mocked) ──

@pytest.fixture
def fake_typst(monkeypatch):
    state = {'returncode': 0, 'stderr': ''}

    def fake_run(cmd, **_kwargs):
        output = cmd[-1]
        if state['returncode'] == 0:
            if '{n}' in output:
                Path(output.replace('{n}', '1')).write_text('<svg/>')
            else:
                Path(output).write_bytes(b'%PDF-fake')
        return SimpleNamespace(returncode=state['returncode'], stderr=state['stderr'])

    monkeypatch.setattr(subprocess, 'run', fake_run)
    return state


@pytest.fixture
def doc(acl_bucket):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'sub/doc.typ', 'hello')


def test_compile_svg(login, doc, fake_typst):  # pylint: disable=unused-argument
    assert login(VIEWER).get('/api/buckets/proj/compile/svg/sub/doc.typ').json() == {
        'pages': ['<svg/>'],
    }


def test_compile_pdf(login, doc, fake_typst):  # pylint: disable=unused-argument
    resp = login(VIEWER).get('/api/buckets/proj/compile/pdf/sub/doc.typ')
    assert resp.content == b'%PDF-fake'
    assert resp.headers['content-type'] == 'application/pdf'
    assert 'doc.pdf' in resp.headers['content-disposition']


def test_compile_missing_is_404(login, doc, fake_typst):  # pylint: disable=unused-argument
    client = login(VIEWER)
    assert client.get('/api/buckets/proj/compile/svg/ghost.typ').status_code == 404
    assert client.get('/api/buckets/proj/compile/pdf/ghost.typ').status_code == 404


def test_compile_error_is_422_with_diagnostics(login, doc, fake_typst):  # pylint: disable=unused-argument
    bucket_dir = (config.TINO_BUCKET_DIR / 'proj').resolve()
    fake_typst.update(returncode=1, stderr=(
        'error: unknown variable: foo\n'
        f'  ┌─ {bucket_dir}/sub/doc.typ:3:2\n'
        '  │\n'
        '3 │ #foo\n'
    ))
    client = login(VIEWER)
    for fmt in ('svg', 'pdf'):
        resp = client.get(f'/api/buckets/proj/compile/{fmt}/sub/doc.typ')
        assert resp.status_code == 422
        detail = resp.json()['detail']
        assert 'unknown variable' in detail['message']
        assert str(bucket_dir) not in detail['message']
        assert detail['diagnostics'] == [{
            'severity': 'error', 'message': 'unknown variable: foo',
            'file': 'sub/doc.typ', 'line': 3, 'column': 2,
        }]


def test_compile_forbidden(login, doc):  # pylint: disable=unused-argument
    assert login(NOBODY).get('/api/buckets/proj/compile/svg/sub/doc.typ').status_code == 403


# ── templates ──

def test_universe_templates(login, monkeypatch):
    monkeypatch.setattr(template_module.httpx, 'get', lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: [{'name': 't', 'version': '1.0.0', 'template': {'entrypoint': 'm.typ'}}],
    ))
    [tpl] = login(NOBODY).get('/api/templates/typst-universe').json()
    assert (tpl['name'], tpl['versions']) == ('t', ['1.0.0'])


def test_local_templates(login, app_env):  # pylint: disable=unused-argument
    pkg = config.TINO_PACKAGE_DIR / 'local' / 'memo' / '1.0.0'
    pkg.mkdir(parents=True)
    (pkg / 'typst.toml').write_text('[package]\n[template]\n')
    assert [t['name'] for t in login(NOBODY).get('/api/templates/local').json()] == ['memo']


@pytest.mark.parametrize('returncode, stderr, existing, status', [
    (0, '', None, 200),
    (1, 'boom', None, 422),
    (0, '', 'main.typ', 409),
])
def test_init_template(login, acl_bucket, monkeypatch,  # pylint: disable=unused-argument,too-many-arguments
                       returncode, stderr, existing, status):
    def fake_run(cmd, **_kwargs):
        if returncode == 0:
            Path(cmd[-1]).mkdir(parents=True)
            (Path(cmd[-1]) / 'main.typ').write_text('tpl')
        return SimpleNamespace(returncode=returncode, stderr=stderr)

    monkeypatch.setattr(subprocess, 'run', fake_run)
    if existing:
        dependencies.get_file_service().write('proj', existing, 'mine')

    resp = login(EDITOR).post('/api/buckets/proj/init-template',
                              json={'name': 't', 'version': '1.0.0'})
    assert resp.status_code == status


def test_init_template_requires_editor(login, acl_bucket):  # pylint: disable=unused-argument
    resp = login(VIEWER).post('/api/buckets/proj/init-template',
                              json={'name': 't', 'version': '1.0.0'})
    assert resp.status_code == 403


# ── misc ──

def test_health(client, app_buckets):
    app_buckets.create('one')
    data = client.get('/health').json()
    assert data['status'] == 'ok'
    assert data['buckets'] == 1
    assert 'version' in data and 'typst' in data


def test_frontend_config(client, monkeypatch):
    monkeypatch.setattr(config, 'TINO_SAVE_DEBOUNCE_MS', 123)
    assert client.get('/api/config').json()['saveDebounceMs'] == 123


def test_theme_css(client, monkeypatch):
    monkeypatch.setattr(config, 'TINO_ACCENT_COLOUR', 'azure')
    resp = client.get('/api/theme.css')
    assert resp.headers['content-type'].startswith('text/css')
    assert '--accent-60:var(--cd-azure-60)' in resp.text


def test_mcp_instructions_admin_only(login, admin_client, monkeypatch):
    monkeypatch.setattr(config, 'TINO_MCP_INSTRUCTIONS', 'House style: be brief.')
    assert 'House style: be brief.' in admin_client.get('/api/mcp/instructions').json()[
        'instructions']
    assert login(EDITOR).get('/api/mcp/instructions').status_code == 403


def test_protected_resource_metadata(client, monkeypatch):
    assert client.get('/.well-known/oauth-protected-resource').status_code == 404
    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', True)
    data = client.get('/.well-known/oauth-protected-resource').json()
    assert data['resource'] == 'http://localhost:8000'
    assert data['authorization_servers'] == ['http://localhost:8000']


def _mock_upstream(app, handler):
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_authorization_server_proxy_injects_none(client, app, monkeypatch):
    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', True)
    monkeypatch.setattr(config, 'TINO_OIDC_DISCOVERY_URL', 'https://sso.example/.well-known/x')
    _mock_upstream(app, lambda req: httpx.Response(200, json={
        'issuer': 'https://sso.example',
        'token_endpoint_auth_methods_supported': ['client_secret_basic'],
    }))
    data = client.get('/.well-known/oauth-authorization-server').json()
    assert data['issuer'] == 'https://sso.example'
    assert data['token_endpoint_auth_methods_supported'] == ['client_secret_basic', 'none']


def test_authorization_server_proxy_upstream_down(client, app, monkeypatch):
    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', True)
    monkeypatch.setattr(config, 'TINO_OIDC_DISCOVERY_URL', 'https://sso.example/.well-known/x')
    _mock_upstream(app, lambda req: httpx.Response(503))
    assert client.get('/.well-known/oauth-authorization-server').status_code == 502


def test_authorization_server_proxy_disabled(client):
    assert client.get('/.well-known/oauth-authorization-server').status_code == 404
