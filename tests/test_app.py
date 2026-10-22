'''Tests for the application factory and its lifespan.'''

import shutil

from fastapi.testclient import TestClient

from tino import config, dependencies


def test_lifespan_creates_dirs_and_flushes_rooms(app, app_env, monkeypatch):
    monkeypatch.setattr(config, 'TINO_AUTH_DISABLED', True)
    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', False)
    shutil.rmtree(config.TINO_FONT_DIR)

    with TestClient(app, base_url='http://localhost') as client:
        assert config.TINO_FONT_DIR.is_dir()
        assert config.TINO_PACKAGE_DIR.is_dir()
        assert client.get('/api/me').json()['username'] == 'tino'
        assert app.state.http_client is not None

    assert app_env.is_dir()
    assert dependencies.get_collab_manager()._ttl_tasks == {}  # pylint: disable=protected-access


def test_mcp_is_mounted_only_when_enabled(app_env, monkeypatch):  # pylint: disable=unused-argument
    from tino.app import create_app  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr('logging.basicConfig', lambda **_: None)

    def mounts(application):
        return [getattr(r, 'path', None) for r in application.routes]

    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', False)
    assert '/mcp' not in mounts(create_app())

    monkeypatch.setattr(config, 'TINO_MCP_ENABLED', True)
    assert '/mcp' in mounts(create_app())


def test_static_frontend_is_served(admin_client):
    resp = admin_client.get('/')
    assert resp.status_code == 200
    assert 'text/html' in resp.headers['content-type']
