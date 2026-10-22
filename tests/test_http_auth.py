'''HTTP tests for authentication: middleware gate, sessions, API keys and OIDC routes.'''

import pytest

from tino import auth, config

from .conftest import ADMIN, EDITOR


# ── Middleware gate ──

def test_api_requires_auth(client):
    resp = client.get('/api/buckets')
    assert resp.status_code == 401
    assert resp.json() == {'detail': 'Not authenticated'}


def test_browser_redirects_to_login(client):
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers['location'] == '/login'


@pytest.mark.parametrize('path', ['/health', '/api/config', '/api/theme.css', '/login'])
def test_public_paths(client, path):
    assert client.get(path).status_code == 200


def test_invalid_bearer_rejected_at_gate(client):
    resp = client.get('/api/buckets', headers={'Authorization': 'Bearer tino_bogus'})
    assert resp.status_code == 401
    assert resp.json() == {'detail': 'Invalid API key'}


def test_tampered_session_cookie_is_ignored(client):
    client.cookies.set('session', 'garbage.value.sig')
    assert client.get('/api/me').status_code == 401


def test_auth_disabled_returns_noauth_admin(client, monkeypatch):
    monkeypatch.setattr(config, 'TINO_AUTH_DISABLED', True)
    resp = client.get('/api/me')
    assert resp.status_code == 200
    assert resp.json()['username'] == 'tino'


# ── /api/me ──

def test_me_admin(login):
    data = login(ADMIN).get('/api/me').json()
    assert data['username'] == 'admin'
    assert data['is_admin'] is True
    assert data['api_key_access'] is None


def test_me_regular_user(login):
    data = login(EDITOR).get('/api/me').json()
    assert data['is_admin'] is False
    assert data['groups'] == ['team-editors']


def test_me_api_key_user(client):
    raw, rec = auth.get_api_key_service().create('ci', {'proj': 'viewer'})
    data = client.get('/api/me', headers={'Authorization': f'Bearer {raw}'}).json()
    assert data['username'] == f'apikey:{rec["id"]}'
    assert data['api_key_access'] == {'proj': 'viewer'}
    assert data['is_admin'] is False


def test_get_current_user_rejects_invalid_bearer_directly():
    '''The dependency itself rejects bad keys too (defence in depth behind the gate).'''
    from fastapi import HTTPException  # pylint: disable=import-outside-toplevel
    from starlette.requests import Request  # pylint: disable=import-outside-toplevel

    request = Request({'type': 'http', 'path': '/x', 'headers': [
        (b'authorization', b'Bearer tino_nope')], 'session': {}})
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(request)
    assert exc.value.status_code == 401


# ── OIDC routes (provider faked) ──

class _FakeOIDC:  # pylint: disable=too-few-public-methods
    '''Minimal stand-in for authlib's registered OIDC client.'''

    def __init__(self, token, userinfo=None, metadata=None, userinfo_error=False):
        self.token = token
        self._userinfo = userinfo or {}
        self.server_metadata = metadata or {}
        self._userinfo_error = userinfo_error
        self.redirect_uri = None

    async def authorize_redirect(self, _request, redirect_uri):
        from starlette.responses import RedirectResponse  # pylint: disable=import-outside-toplevel
        self.redirect_uri = redirect_uri
        return RedirectResponse('https://sso.example/auth')

    async def authorize_access_token(self, _request):
        return self.token

    async def userinfo(self, token):  # pylint: disable=unused-argument
        if self._userinfo_error:
            raise RuntimeError('userinfo down')
        return self._userinfo

    async def load_server_metadata(self):
        return self.server_metadata


@pytest.fixture
def fake_oidc(monkeypatch):
    def _install(**kwargs):
        oidc = _FakeOIDC(**kwargs)
        monkeypatch.setattr(auth.oauth, 'oidc', oidc, raising=False)
        return oidc
    return _install


def test_oidc_login_redirects_with_callback(client, fake_oidc):
    oidc = fake_oidc(token={})
    resp = client.get('/oidc/login', follow_redirects=False)
    assert resp.headers['location'] == 'https://sso.example/auth'
    assert oidc.redirect_uri == 'http://localhost:8000/oidc/callback'


def test_callback_creates_session_from_id_token(client, fake_oidc):
    fake_oidc(token={'id_token': 'idt', 'userinfo': {
        'preferred_username': 'alice', 'email': 'a@x', 'groups': ['admins']}})
    resp = client.get('/oidc/callback', follow_redirects=False)
    assert resp.status_code == 307
    me = client.get('/api/me').json()
    assert me['username'] == 'alice'
    assert me['is_admin'] is True


def test_callback_merges_userinfo_endpoint(client, fake_oidc):
    fake_oidc(
        token={'userinfo': {'sub': 'sub-1'}},
        userinfo={'email': 'b@x', 'groups': ['team']},
        metadata={'userinfo_endpoint': 'https://sso.example/userinfo'},
    )
    client.get('/oidc/callback', follow_redirects=False)
    me = client.get('/api/me').json()
    assert (me['username'], me['email'], me['groups']) == ('sub-1', 'b@x', ['team'])


def test_callback_survives_failing_userinfo(client, fake_oidc):
    fake_oidc(
        token={'userinfo': {'preferred_username': 'carol'}},
        metadata={'userinfo_endpoint': 'https://sso.example/userinfo'},
        userinfo_error=True,
    )
    client.get('/oidc/callback', follow_redirects=False)
    assert client.get('/api/me').json()['username'] == 'carol'


def test_callback_custom_groups_claim(client, fake_oidc, monkeypatch):
    monkeypatch.setattr(config, 'TINO_OIDC_GROUPS_CLAIM', 'roles')
    fake_oidc(token={'userinfo': {'sub': 'x', 'roles': ['r1'], 'groups': ['ignored']}})
    client.get('/oidc/callback', follow_redirects=False)
    assert client.get('/api/me').json()['groups'] == ['r1']


def test_callback_without_userinfo_is_400(client, fake_oidc):
    fake_oidc(token={})
    assert client.get('/oidc/callback', follow_redirects=False).status_code == 400


def test_logout_with_end_session_endpoint(login, fake_oidc):
    fake_oidc(token={}, metadata={'end_session_endpoint': 'https://sso.example/logout'})
    resp = login(ADMIN).get('/logout', follow_redirects=False)
    location = resp.headers['location']
    assert location.startswith('https://sso.example/logout?')
    assert 'post_logout_redirect_uri=http://localhost:8000/login' in location
    assert 'id_token_hint' not in location
    assert resp.headers['set-cookie'].startswith('session=null;')


def test_logout_includes_id_token_hint(client, fake_oidc):
    oidc = fake_oidc(token={'id_token': 'idt', 'userinfo': {'sub': 'x'}},
                     metadata={'end_session_endpoint': 'https://sso.example/logout'})
    client.get('/oidc/callback', follow_redirects=False)
    oidc.server_metadata = {'end_session_endpoint': 'https://sso.example/logout'}
    location = client.get('/logout', follow_redirects=False).headers['location']
    assert 'id_token_hint=idt' in location


def test_logout_without_end_session_endpoint(login, fake_oidc):
    fake_oidc(token={})
    resp = login(ADMIN).get('/logout', follow_redirects=False)
    assert resp.headers['location'] == '/login'


# ── Middleware extras ──

def test_large_responses_are_gzipped(admin_client, app_buckets):
    app_buckets.create('big', description='x' * 5000)
    resp = admin_client.get('/api/buckets', headers={'Accept-Encoding': 'gzip'})
    assert resp.headers.get('content-encoding') == 'gzip'
