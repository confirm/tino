'''Shared fixtures for the TINO test suite.

Every service is bound to a fresh ``tmp_path`` per test, so the suite touches
only throwaway directories and never the developer's real data dir.

HTTP tests use the ``client`` fixture: a :class:`~fastapi.testclient.TestClient`
around a freshly created app whose config points at ``tmp_path``. The app's
lifespan is deliberately *not* run, so no OIDC discovery or sanity checks
happen; authentication is exercised via signed session cookies (``login``) or
API-key bearer tokens.
'''

import json
import logging
from base64 import b64encode

import httpx
import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from tino import auth, config, dependencies
from tino.models import AccessEntry, User
from tino.services.api_keys import ApiKeyService
from tino.services.bucket import BucketService
from tino.services.file import FileService
from tino.services.git import GitService

SECRET_KEY = 'test-secret-key'

ADMIN  = User(username='admin', email='admin@tino', groups=['admins'])
EDITOR = User(username='ed', email='ed@tino', groups=['team-editors'])
VIEWER = User(username='vi', email='vi@tino', groups=['team-viewers'])
COMMIT = User(username='co', email='co@tino', groups=['team-committers'])
NOBODY = User(username='no', email='no@tino', groups=['outsiders'])

#: ACL used by the ``acl_bucket`` fixture; maps the users above to their roles.
ACL = [
    AccessEntry(group='team-viewers', role='viewer'),
    AccessEntry(group='team-editors', role='editor'),
    AccessEntry(group='team-committers', role='committer'),
]

_FACTORIES = (
    dependencies.get_bucket_service,
    dependencies.get_collab_manager,
    dependencies.get_compiler_service,
    dependencies.get_file_service,
    dependencies.get_font_service,
    dependencies.get_git_service,
    dependencies.get_notifier,
    dependencies.get_search_service,
    dependencies.get_template_service,
)


@pytest.fixture(autouse=True)
def _git_identity(monkeypatch):
    '''Give git an author/committer so bucket commits work on a bare CI runner.'''
    monkeypatch.setenv('GIT_AUTHOR_NAME', 'Test')
    monkeypatch.setenv('GIT_AUTHOR_EMAIL', 'test@tino')
    monkeypatch.setenv('GIT_COMMITTER_NAME', 'Test')
    monkeypatch.setenv('GIT_COMMITTER_EMAIL', 'test@tino')


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    '''Pin auth-related config so role tests are deterministic regardless of env.'''
    monkeypatch.setattr(config, 'TINO_ADMIN_GROUPS', {'admins'})
    monkeypatch.setattr(config, 'TINO_DEFAULT_ROLE', 'none')
    monkeypatch.setattr(config, 'TINO_AUTH_DISABLED', False)


@pytest.fixture
def anyio_backend():
    '''Run ``@pytest.mark.anyio`` tests on asyncio only (pycrdt needs asyncio).'''
    return 'asyncio'


@pytest.fixture
def data_dir(tmp_path):
    '''A fresh, isolated data directory for each test.'''
    return tmp_path


@pytest.fixture
def buckets(data_dir):
    return BucketService(data_dir)


@pytest.fixture
def files(data_dir):
    return FileService(data_dir)


@pytest.fixture
def git_svc(data_dir):
    return GitService(data_dir)


@pytest.fixture
def api_keys(data_dir):
    return ApiKeyService(data_dir / 'api_keys.yml')


@pytest.fixture
def bucket(buckets):
    '''A ready-made, git-backed bucket; returns its slug.'''
    buckets.create('demo', description='Demo bucket')
    return 'demo'


# ── App / HTTP fixtures ──


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    '''Point every config directory at ``tmp_path`` and reset service singletons.

    Returns the bucket directory. The ``lru_cache`` factories in
    :mod:`tino.dependencies` are cleared before and after, so each test gets
    services bound to its own temp dirs.
    '''
    bucket_dir = tmp_path / 'buckets'
    font_dir   = tmp_path / 'fonts'
    bucket_dir.mkdir()
    font_dir.mkdir()

    monkeypatch.setattr(config, 'TINO_DATA_DIR', tmp_path)
    monkeypatch.setattr(config, 'TINO_BUCKET_DIR', bucket_dir)
    monkeypatch.setattr(config, 'TINO_PACKAGE_DIR', tmp_path / 'packages')
    monkeypatch.setattr(config, 'TINO_FONT_DIR', font_dir)
    monkeypatch.setattr(config, 'TINO_SECRET_KEY', SECRET_KEY)
    monkeypatch.setattr(config, 'TINO_BASE_URL', 'http://localhost:8000')
    monkeypatch.setattr(auth, '_api_key_service', ApiKeyService(tmp_path / 'api_keys.yml'))

    for factory in _FACTORIES:
        factory.cache_clear()
    yield bucket_dir
    for factory in _FACTORIES:
        factory.cache_clear()


@pytest.fixture
def app(app_env, monkeypatch):  # pylint: disable=unused-argument
    '''A freshly built TINO app (lifespan not started).'''
    from tino.app import create_app  # pylint: disable=import-outside-toplevel

    # create_app() calls basicConfig(force=True), which would rip out pytest's
    # log-capture handlers; skip it.
    monkeypatch.setattr(logging, 'basicConfig', lambda **_: None)
    application = create_app()
    application.state.http_client = httpx.AsyncClient()
    return application


@pytest.fixture
def client(app):
    '''An HTTP test client for the app (no cookies, i.e. anonymous).

    Not used as a context manager on purpose: that would run the lifespan.
    '''
    test_client = TestClient(app, base_url='http://localhost')
    yield test_client
    test_client.close()


def session_cookie(user: User) -> str:
    '''Build a signed Starlette session cookie value holding *user*.'''
    data = b64encode(json.dumps({'user': user.model_dump()}).encode('utf-8'))
    return TimestampSigner(SECRET_KEY).sign(data).decode('utf-8')


@pytest.fixture
def login(client):
    '''Return a callable that logs *client* in as the given user.'''
    def _login(user: User = ADMIN) -> TestClient:
        client.cookies.set('session', session_cookie(user))
        return client
    return _login


@pytest.fixture
def admin_client(login):
    '''A client logged in as a global admin.'''
    return login(ADMIN)


@pytest.fixture
def app_buckets(app_env):  # pylint: disable=unused-argument
    '''The app's own BucketService singleton (same instance the routes use).'''
    return dependencies.get_bucket_service()


@pytest.fixture
def acl_bucket(app_buckets):
    '''A bucket named ``proj`` with the :data:`ACL` access list; returns its slug.'''
    app_buckets.create('proj', description='Project', access=ACL)
    return 'proj'
