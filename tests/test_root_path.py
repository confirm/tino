'''Tests for serving TINO under a sub-path (e.g. https://example.com/tino).

The reverse proxy may forward requests with the prefix or strip it, so most
checks run against both forms.
'''

import os
import subprocess
import sys

import httpx
import pytest
from fastapi.testclient import TestClient

from tino import auth, config
from tino.middleware import route_path

from .conftest import ADMIN, VIEWER, session_cookie
from .test_http_auth import _FakeOIDC

ROOT = '/tino'


@pytest.fixture
def sub_app(app_env, monkeypatch):  # pylint: disable=unused-argument
    '''An app configured for https://…/tino (config is read at creation time).'''
    from tino.app import create_app  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(config, 'TINO_BASE_URL', f'http://localhost:8000{ROOT}')
    monkeypatch.setattr(config, 'TINO_ROOT_PATH', ROOT)
    monkeypatch.setattr('logging.basicConfig', lambda **_: None)
    application = create_app()
    application.state.http_client = httpx.AsyncClient()
    return application


@pytest.fixture
def sub_client(sub_app):
    test_client = TestClient(sub_app, base_url='http://localhost')
    yield test_client
    test_client.close()


@pytest.fixture
def sub_login(sub_client):
    def _login(user=ADMIN):
        sub_client.cookies.set('session', session_cookie(user))
        return sub_client
    return _login


# ── config ──

@pytest.mark.parametrize('base_url, expected', [
    ('https://tino.example.com', ''),
    ('https://example.com/tino', '/tino'),
    ('https://example.com/apps/tino/', '/apps/tino'),
])
def test_root_path_is_derived_from_base_url(base_url, expected):
    env = {**os.environ, 'TINO_BASE_URL': base_url}
    out = subprocess.run(
        [sys.executable, '-c', 'from tino.config import TINO_ROOT_PATH as r; print(repr(r))'],
        env=env, capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == repr(expected)


@pytest.mark.parametrize('path, root, expected', [
    ('/tino/login', '/tino', '/login'),
    ('/tino', '/tino', '/'),
    ('/tinofoo', '/tino', '/tinofoo'),
    ('/login', '', '/login'),
])
def test_route_path(path, root, expected):
    assert route_path({'path': path, 'root_path': root}) == expected


# ── HTTP ──

def test_bare_prefix_redirects_to_trailing_slash(sub_client):
    resp = sub_client.get(ROOT, follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers['location'] == f'{ROOT}/'
    resp = sub_client.get(f'{ROOT}?a=1', follow_redirects=False)
    assert resp.headers['location'] == f'{ROOT}/?a=1'


@pytest.mark.parametrize('prefix', [ROOT, ''])
def test_public_and_api_routes(sub_client, prefix):
    assert sub_client.get(f'{prefix}/health').json()['status'] == 'ok'
    assert sub_client.get(f'{prefix}/api/buckets').status_code == 401


@pytest.mark.parametrize('prefix', [ROOT, ''])
def test_anonymous_browser_redirects_to_prefixed_login(sub_client, prefix):
    resp = sub_client.get(f'{prefix}/', follow_redirects=False)
    assert resp.headers['location'] == f'{ROOT}/login'


def test_login_page_uses_relative_urls(sub_client):
    html = sub_client.get(f'{ROOT}/login').text
    assert 'href="oidc/login"' in html
    assert 'href="/' not in html and 'src="/' not in html


@pytest.mark.parametrize('prefix', [ROOT, ''])
def test_authenticated_requests(sub_login, prefix):
    client = sub_login(ADMIN)
    assert client.get(f'{prefix}/api/me').json()['username'] == 'admin'
    index = client.get(f'{prefix}/')
    assert index.status_code == 200
    assert 'href="api/theme.css"' in index.text
    assert client.get(f'{prefix}/js/urls.js').status_code == 200


@pytest.mark.parametrize('prefix', [ROOT, ''])
def test_websocket_events(sub_login, acl_bucket, prefix):  # pylint: disable=unused-argument
    client = sub_login(VIEWER)
    with client.websocket_connect(f'{prefix}/api/buckets/proj/events') as ws:
        ws.send_text('ping')


# ── OIDC redirects & session cookie ──

@pytest.fixture
def fake_oidc(monkeypatch):
    oidc = _FakeOIDC(token={'userinfo': {'sub': 'alice'}})
    monkeypatch.setattr(auth.oauth, 'oidc', oidc, raising=False)
    return oidc


def test_callback_redirects_into_prefix_and_scopes_cookie(sub_client, fake_oidc):  # pylint: disable=unused-argument
    resp = sub_client.get(f'{ROOT}/oidc/callback', follow_redirects=False)
    assert resp.headers['location'] == f'{ROOT}/'
    assert 'path=/tino' in resp.headers['set-cookie'].lower()


def test_oidc_login_uses_prefixed_callback(sub_client, fake_oidc):
    sub_client.get(f'{ROOT}/oidc/login', follow_redirects=False)
    assert fake_oidc.redirect_uri == f'http://localhost:8000{ROOT}/oidc/callback'


def test_logout_falls_back_to_prefixed_login(sub_login, fake_oidc):  # pylint: disable=unused-argument
    resp = sub_login(ADMIN).get(f'{ROOT}/logout', follow_redirects=False)
    assert resp.headers['location'] == f'{ROOT}/login'


# ── MCP OAuth discovery ──

@pytest.mark.parametrize('path', [
    '/.well-known/oauth-protected-resource/tino/mcp',   # host root, path-inserted
    f'{ROOT}/.well-known/oauth-protected-resource',
    '/.well-known/oauth-protected-resource',
])
def test_protected_resource_metadata_paths(sub_client, monkeypatch, path):
    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', True)
    resp = sub_client.get(path)
    assert resp.status_code == 200
    assert resp.json()['resource'] == f'http://localhost:8000{ROOT}'


def test_authorization_server_metadata_path_inserted(sub_client, sub_app, monkeypatch):
    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', True)
    monkeypatch.setattr(config, 'TINO_OIDC_DISCOVERY_URL', 'https://sso.example/.well-known/x')
    sub_app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={'issuer': 'https://sso.example'})))
    resp = sub_client.get('/.well-known/oauth-authorization-server/tino')
    assert resp.json()['token_endpoint_auth_methods_supported'] == ['none']
