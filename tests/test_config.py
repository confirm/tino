'''Tests for the startup sanity checks in tino.config.'''

import pytest

from tino import config


@pytest.fixture
def valid(tmp_path, monkeypatch):
    '''A fully valid configuration; tests break one setting at a time.'''
    for name, value in {
        'TINO_DATA_DIR': tmp_path,
        'TINO_BASE_URL': 'https://tino.example.com',
        'TINO_ADMIN_GROUPS': {'admins'},
        'TINO_AUTH_DISABLED': False,
        'TINO_OIDC_DISCOVERY_URL': 'https://sso.example/.well-known/openid-configuration',
        'TINO_OIDC_CLIENT_ID': 'tino',
        'TINO_OIDC_CLIENT_SECRET': 's3cret',
        'TINO_OIDC_GROUPS_CLAIM': 'groups',
        'TINO_DEFAULT_ROLE': 'none',
        'TINO_ACCENT_COLOUR': 'orange',
        'TINO_MCP_ENABLED': False,
    }.items():
        monkeypatch.setattr(config, name, value)
    return monkeypatch


def test_valid_config_passes(valid):  # pylint: disable=unused-argument
    config.sanity_checks()


@pytest.mark.parametrize('url', ['http://localhost:8000', 'http://127.0.0.1:8000'])
def test_local_http_base_url_allowed(valid, url):
    valid.setattr(config, 'TINO_BASE_URL', url)
    config.sanity_checks()


def test_auth_disabled_skips_oidc_checks(valid):
    valid.setattr(config, 'TINO_AUTH_DISABLED', True)
    valid.setattr(config, 'TINO_OIDC_DISCOVERY_URL', None)
    valid.setattr(config, 'TINO_OIDC_CLIENT_SECRET', None)
    config.sanity_checks()


@pytest.mark.parametrize('name, value', [
    ('TINO_BASE_URL', None),
    ('TINO_BASE_URL', 'http://tino.example.com'),
    ('TINO_ADMIN_GROUPS', set()),
    ('TINO_OIDC_DISCOVERY_URL', None),
    ('TINO_OIDC_CLIENT_ID', ''),
    ('TINO_OIDC_CLIENT_SECRET', None),
    ('TINO_OIDC_GROUPS_CLAIM', ''),
    ('TINO_DEFAULT_ROLE', 'admin'),
    ('TINO_ACCENT_COLOUR', 'pink'),
])
def test_invalid_setting_exits(valid, name, value):
    valid.setattr(config, name, value)
    with pytest.raises(SystemExit) as exc:
        config.sanity_checks()
    assert exc.value.code == 1


def test_missing_data_dir_exits(valid, tmp_path):
    valid.setattr(config, 'TINO_DATA_DIR', tmp_path / 'missing')
    with pytest.raises(SystemExit):
        config.sanity_checks()


def test_readonly_data_dir_exits(valid, monkeypatch):
    monkeypatch.setattr(config.os, 'access', lambda *_: False)
    with pytest.raises(SystemExit):
        config.sanity_checks()
