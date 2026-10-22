'''Tests for the role-resolution and access-control logic in tino.auth.'''

import pytest
from fastapi import HTTPException

from tino import config
from tino.auth import check_access, is_global_admin, resolve_role
from tino.models import AccessEntry, User


def _user(*groups, api_key_access=None):
    return User(username='u', email='u@x', groups=list(groups),
                api_key_access=api_key_access)


# ── is_global_admin ──

def test_admin_group_is_admin():
    assert is_global_admin(_user('admins')) is True


def test_non_admin_group_is_not_admin():
    assert is_global_admin(_user('employees')) is False


# ── resolve_role (OIDC users) ──

def test_admin_resolves_to_committer():
    assert resolve_role(_user('admins'), []) == 'committer'


def test_no_access_with_default_none_returns_none():
    assert resolve_role(_user('employees'), []) is None


def test_no_access_falls_back_to_default_role(monkeypatch):
    monkeypatch.setattr(config, 'TINO_DEFAULT_ROLE', 'editor')
    assert resolve_role(_user('employees'), []) == 'editor'


def test_group_maps_to_role():
    access = [AccessEntry(group='team', role='editor')]
    assert resolve_role(_user('team'), access) == 'editor'


def test_highest_role_of_multiple_groups_wins():
    access = [
        AccessEntry(group='a', role='viewer'),
        AccessEntry(group='b', role='committer'),
    ]
    assert resolve_role(_user('a', 'b'), access) == 'committer'


def test_no_matching_group_returns_none():
    access = [AccessEntry(group='team', role='editor')]
    assert resolve_role(_user('outsider'), access) is None


# ── resolve_role (API-key users) ──

def test_api_key_user_uses_access_map_not_acl():
    user = _user(api_key_access={'proj': 'editor'})
    # bucket ACL would grant nothing, but the key's own map applies:
    assert resolve_role(user, [AccessEntry(group='x', role='committer')],
                        slug='proj') == 'editor'
    assert resolve_role(user, [], slug='other') is None


def test_api_key_user_without_slug_returns_none():
    user = _user(api_key_access={'proj': 'editor'})
    assert resolve_role(user, []) is None


# ── check_access ──

def test_check_access_admin_passes():
    check_access(_user('admins'), [], 'committer')  # no raise


def test_check_access_sufficient_role_passes():
    access = [AccessEntry(group='team', role='committer')]
    check_access(_user('team'), access, 'editor')  # committer >= editor


def test_check_access_insufficient_role_raises_403():
    access = [AccessEntry(group='team', role='viewer')]
    with pytest.raises(HTTPException) as exc:
        check_access(_user('team'), access, 'editor')
    assert exc.value.status_code == 403


def test_check_access_no_access_raises_403():
    with pytest.raises(HTTPException) as exc:
        check_access(_user('outsider'), [], 'viewer')
    assert exc.value.status_code == 403
