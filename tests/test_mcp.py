'''Tests for the MCP server: tools, authorization and OIDC token verification.'''

import base64
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pycrdt import Text

from tino import config, dependencies
from tino.mcp import instructions
from tino.mcp import server as mcp
from tino.models import FileEdit

from .conftest import ADMIN, COMMIT, EDITOR, NOBODY, VIEWER


@pytest.fixture
def as_user(app_env):  # pylint: disable=unused-argument
    '''Return a callable binding the MCP request context to a user.

    Async tests run in a copied context, so their tokens can't be ``reset()``
    here; clearing the variable is enough.
    '''
    def _bind(user):
        mcp._current_user.set(user)  # pylint: disable=protected-access

    yield _bind
    mcp._current_user.set(None)  # pylint: disable=protected-access


@pytest.fixture
def proj(acl_bucket):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'main.typ', '= Hello\nneedle')
    return 'proj'


# ── helpers ──

@pytest.mark.parametrize('url, issuer', [
    ('https://sso/realms/x/.well-known/openid-configuration', 'https://sso/realms/x'),
    ('https://sso/realms/x', 'https://sso/realms/x'),
])
def test_issuer_url(url, issuer):
    assert mcp._issuer_url(url) == issuer  # pylint: disable=protected-access


def test_server_instructions(monkeypatch):
    monkeypatch.setattr(config, 'TINO_MCP_INSTRUCTIONS', None)
    assert instructions.server_instructions() == instructions.BASE_INSTRUCTIONS
    monkeypatch.setattr(config, 'TINO_MCP_INSTRUCTIONS', 'Extra.')
    assert instructions.server_instructions().endswith('\nExtra.\n')


def test_build_auth_kwargs(monkeypatch):
    monkeypatch.setattr(config, 'TINO_AUTH_DISABLED', True)
    assert mcp._build_auth_kwargs() == {}  # pylint: disable=protected-access

    monkeypatch.setattr(config, 'TINO_AUTH_DISABLED', False)
    monkeypatch.setattr(config, 'TINO_OIDC_DISCOVERY_URL', None)
    assert mcp._build_auth_kwargs() == {}  # pylint: disable=protected-access

    monkeypatch.setattr(config, 'TINO_OIDC_DISCOVERY_URL',
                        'https://sso/.well-known/openid-configuration')
    monkeypatch.setattr(config, 'TINO_BASE_URL', 'https://tino.example')
    kwargs = mcp._build_auth_kwargs()  # pylint: disable=protected-access
    assert isinstance(kwargs['token_verifier'], mcp.OIDCTokenVerifier)
    assert str(kwargs['auth'].resource_server_url) == 'https://tino.example/mcp'


# ── authorization ──

def test_unauthenticated_tools_raise(app_env):  # pylint: disable=unused-argument
    with pytest.raises(PermissionError):
        mcp.list_buckets()
    with pytest.raises(PermissionError):
        mcp.search('needle')
    with pytest.raises(PermissionError):
        mcp.list_files('proj')


def test_require_missing_bucket(as_user):
    as_user(ADMIN)
    with pytest.raises(FileNotFoundError):
        mcp.list_files('ghost')


def test_require_insufficient_role(as_user, proj):
    as_user(NOBODY)
    with pytest.raises(PermissionError):
        mcp.read_file(proj, 'main.typ')


# ── read tools ──

def test_list_buckets(as_user, proj, app_buckets):
    app_buckets.update(proj, name='Project', mcp_instructions='Write German.')
    app_buckets.create('hidden')
    as_user(VIEWER)
    assert mcp.list_buckets() == [{
        'slug': 'proj', 'description': 'Project', 'role': 'viewer',
        'name': 'Project', 'instructions': 'Write German.',
    }]


def test_list_files(as_user, proj):
    as_user(VIEWER)
    assert mcp.list_files(proj) == [{'path': 'main.typ', 'type': 'file'}]


def test_read_file(as_user, proj):
    as_user(VIEWER)
    assert mcp.read_file(proj, 'main.typ') == '= Hello\nneedle'


def test_read_file_prefers_live_room(as_user, proj, monkeypatch):
    as_user(VIEWER)
    monkeypatch.setattr(dependencies.get_collab_manager(), 'get_content',
                        lambda slug, path: 'live')
    assert mcp.read_file(proj, 'main.typ') == 'live'


def test_read_file_missing_and_binary(as_user, proj):
    dependencies.get_file_service().upload(proj, 'img.png', b'\xff\xfe')
    as_user(VIEWER)
    with pytest.raises(FileNotFoundError):
        mcp.read_file(proj, 'ghost.typ')
    with pytest.raises(ValueError, match='binary'):
        mcp.read_file(proj, 'img.png')


@pytest.fixture
def long_file(proj):
    dependencies.get_file_service().write(proj, 'long.typ', '\n'.join(f'line {n}' for n in range(1, 11)))
    return 'long.typ'


def test_read_file_range(as_user, proj, long_file):
    as_user(VIEWER)
    assert mcp.read_file(proj, long_file, offset=3, limit=2) == '     3\tline 3\n     4\tline 4'


def test_read_file_offset_only_and_limit_only(as_user, proj, long_file):
    as_user(VIEWER)
    assert mcp.read_file(proj, long_file, offset=10) == '    10\tline 10'
    assert mcp.read_file(proj, long_file, limit=1) == '     1\tline 1'
    assert mcp.read_file(proj, long_file, offset=9, limit=50).count('\n') == 1


def test_read_file_range_matches_search_line_numbers(as_user, proj, long_file):
    as_user(VIEWER)
    [hit] = mcp.search('line 7', bucket=proj)
    line = hit['snippets'][0]['line']
    assert mcp.read_file(proj, long_file, offset=line, limit=1).endswith('\tline 7')


@pytest.mark.parametrize('offset, limit, message', [
    (0, None, 'offset must be 1'),
    (None, 0, 'limit must be 1'),
    (11, None, r'past the end of the file \(10 lines\)'),
])
def test_read_file_invalid_range(as_user, proj, long_file, offset, limit, message):
    as_user(VIEWER)
    with pytest.raises(ValueError, match=message):
        mcp.read_file(proj, long_file, offset=offset, limit=limit)


def test_search(as_user, proj, app_buckets):
    app_buckets.create('hidden')
    dependencies.get_file_service().write('hidden', 'x.typ', 'needle')
    as_user(VIEWER)
    results = mcp.search('needle')
    assert [(r['bucket'], r['path']) for r in results] == [('proj', 'main.typ')]
    assert mcp.search('n') == []
    assert mcp.search('needle', bucket=proj)[0]['snippets'][0]['line'] == 2
    with pytest.raises(PermissionError):
        mcp.search('needle', bucket='hidden')


def test_search_caps_results(as_user, proj, monkeypatch):
    monkeypatch.setattr(mcp, 'MCP_MAX_RESULTS', 1)
    dependencies.get_file_service().write(proj, 'needle.typ', 'x')
    as_user(ADMIN)
    assert len(mcp.search('needle')) == 1


def test_compile_typst(as_user, proj, monkeypatch):
    as_user(VIEWER)
    compiler = dependencies.get_compiler_service()

    monkeypatch.setattr(compiler, 'compile_svg', lambda *_: ['<svg/>', '<svg/>'])
    assert mcp.compile_typst(proj, 'main.typ') == {'success': True, 'pages': 2}

    def fail(*_):
        raise RuntimeError('error: oops')
    monkeypatch.setattr(compiler, 'compile_svg', fail)
    assert mcp.compile_typst(proj, 'main.typ') == {'success': False, 'error': 'error: oops'}

    def missing(*_):
        raise FileNotFoundError('nope')
    monkeypatch.setattr(compiler, 'compile_svg', missing)
    with pytest.raises(FileNotFoundError):
        mcp.compile_typst(proj, 'main.typ')


def test_git_status_and_log(as_user, proj):
    as_user(VIEWER)
    assert mcp.git_status(proj) == [{'path': 'main.typ', 'status': 'untracked'}]
    assert mcp.git_log(proj) == []


# ── write tools ──

@pytest.mark.anyio
async def test_write_tools_require_editor(as_user, proj):
    as_user(VIEWER)
    for call in (
        mcp.write_file(proj, 'x.typ', 'x'),
        mcp.write_binary_file(proj, 'x.png', 'QUJD'),
        mcp.delete_file(proj, 'main.typ'),
        mcp.rename_file(proj, 'main.typ', 'x.typ'),
        mcp.create_dir(proj, 'd'),
        mcp.rename_dir(proj, 'd', 'e'),
        mcp.delete_dir(proj, 'd'),
    ):
        with pytest.raises(PermissionError):
            await call


@pytest.mark.anyio
async def test_write_file(as_user, proj):
    as_user(EDITOR)
    result = await mcp.write_file(proj, 'new.typ', 'content')
    assert result['path'] == 'new.typ'
    assert dependencies.get_file_service().read(proj, 'new.typ')['content'] == 'content'
    with pytest.raises(ValueError):
        await mcp.write_file(proj, '../evil.typ', 'x')


def _edits(*pairs, replace_all=False):
    return [FileEdit(old_string=old, new_string=new, replace_all=replace_all)
            for old, new in pairs]


@pytest.mark.anyio
async def test_edit_file(as_user, proj):
    as_user(EDITOR)
    result = await mcp.edit_file(proj, 'main.typ', _edits(('Hello', 'Hallo'), ('needle', 'pin')))
    assert result['replacements'] == 2
    assert result['modified']
    assert mcp.read_file(proj, 'main.typ') == '= Hallo\npin'


@pytest.mark.anyio
async def test_edit_file_is_atomic(as_user, proj):
    as_user(EDITOR)
    with pytest.raises(ValueError, match='Edit 2'):
        await mcp.edit_file(proj, 'main.typ', _edits(('Hello', 'Hallo'), ('missing', 'x')))
    assert mcp.read_file(proj, 'main.typ') == '= Hello\nneedle'


@pytest.mark.anyio
async def test_edit_file_errors(as_user, proj):
    as_user(EDITOR)
    with pytest.raises(ValueError, match='No edits'):
        await mcp.edit_file(proj, 'main.typ', [])
    with pytest.raises(FileNotFoundError):
        await mcp.edit_file(proj, 'ghost.typ', _edits(('a', 'b')))
    as_user(VIEWER)
    with pytest.raises(PermissionError):
        await mcp.edit_file(proj, 'main.typ', _edits(('Hello', 'x')))


@pytest.mark.anyio
async def test_edit_file_merges_into_open_room(as_user, proj):
    collab = dependencies.get_collab_manager()
    await collab._get_or_create_room(proj, 'main.typ')  # pylint: disable=protected-access
    try:
        room = collab._rooms[(proj, 'main.typ')]  # pylint: disable=protected-access
        room.ydoc.get('content', type=Text).insert(0, '// live\n')

        as_user(EDITOR)
        await mcp.edit_file(proj, 'main.typ', _edits(('needle', 'pin')))

        assert mcp.read_file(proj, 'main.typ') == '// live\n= Hello\npin'
        assert dependencies.get_file_service().read(proj, 'main.typ')['content'] == \
            '// live\n= Hello\npin'
    finally:
        for task in collab._room_tasks.values():  # pylint: disable=protected-access
            task.cancel()


@pytest.mark.anyio
async def test_edit_file_through_mcp_layer(as_user, proj):
    '''Arguments arrive as JSON, so they must validate into FileEdit models.'''
    as_user(EDITOR)
    await mcp.mcp.call_tool('edit_file', {
        'bucket': proj, 'path': 'main.typ',
        'edits': [{'old_string': 'e', 'new_string': 'E', 'replace_all': True}],
    })
    assert mcp.read_file(proj, 'main.typ') == '= HEllo\nnEEdlE'


PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe'


@pytest.mark.anyio
async def test_write_binary_file(as_user, proj):
    as_user(EDITOR)
    result = await mcp.write_binary_file(proj, 'img/logo.png', base64.b64encode(PNG).decode())
    assert result == {'path': 'img/logo.png', 'size': len(PNG)}
    target = dependencies.get_file_service().resolve(proj, 'img/logo.png')
    assert target.read_bytes() == PNG


@pytest.mark.anyio
@pytest.mark.parametrize('wrap', [
    lambda b64: '\n'.join(b64[i:i + 4] for i in range(0, len(b64), 4)) + '\n',
    lambda b64: f'data:image/png;base64,{b64}',
    lambda b64: f'  {b64}\r\n',
])
async def test_write_binary_file_tolerated_formats(as_user, proj, wrap):
    as_user(EDITOR)
    await mcp.write_binary_file(proj, 'logo.png', wrap(base64.b64encode(PNG).decode()))
    assert dependencies.get_file_service().resolve(proj, 'logo.png').read_bytes() == PNG


@pytest.mark.anyio
@pytest.mark.parametrize('content', ['not base64!', 'QUJD=', 'QUJ', 'QU*D'])
async def test_write_binary_file_rejects_invalid_base64(as_user, proj, content):
    as_user(EDITOR)
    with pytest.raises(ValueError, match='not valid base64'):
        await mcp.write_binary_file(proj, 'x.bin', content)
    assert dependencies.get_file_service().resolve(proj, 'x.bin') is None


@pytest.mark.anyio
async def test_write_binary_file_size_cap(as_user, proj, monkeypatch):
    monkeypatch.setattr(mcp, 'MCP_MAX_BINARY_BYTES', 10)
    as_user(EDITOR)

    for size in (8, 9, 10):  # padding variants up to the exact limit
        await mcp.write_binary_file(proj, 'ok.bin', base64.b64encode(b'x' * size).decode())

    for size in (11, 1000):  # just over (exact check) and far over (pre-check)
        with pytest.raises(ValueError, match='too large'):
            await mcp.write_binary_file(proj, 'big.bin', base64.b64encode(b'x' * size).decode())
    assert dependencies.get_file_service().resolve(proj, 'big.bin') is None


@pytest.mark.anyio
async def test_write_binary_file_errors(as_user, proj, data_dir):  # pylint: disable=unused-argument
    as_user(EDITOR)
    with pytest.raises(ValueError, match='Invalid path'):
        await mcp.write_binary_file(proj, '../escape.bin', 'QUJD')
    assert not (config.TINO_BUCKET_DIR / 'escape.bin').exists()

    as_user(VIEWER)
    with pytest.raises(PermissionError):
        await mcp.write_binary_file(proj, 'x.bin', 'QUJD')


@pytest.mark.anyio
async def test_write_binary_file_evicts_open_room(as_user, proj):
    collab = dependencies.get_collab_manager()
    await collab._get_or_create_room(proj, 'main.typ')  # pylint: disable=protected-access
    try:
        as_user(EDITOR)
        await mcp.write_binary_file(proj, 'main.typ', base64.b64encode(PNG).decode())
        assert collab.get_content(proj, 'main.typ') is None
        await collab.shutdown()  # a flush must not overwrite the binary content
        assert dependencies.get_file_service().resolve(proj, 'main.typ').read_bytes() == PNG
    finally:
        for task in collab._room_tasks.values():  # pylint: disable=protected-access
            task.cancel()


@pytest.mark.anyio
async def test_write_binary_file_through_mcp_layer(as_user, proj):
    as_user(EDITOR)
    await mcp.mcp.call_tool('write_binary_file', {
        'bucket': proj, 'path': 'a.bin', 'content_base64': 'AAEC',
    })
    assert dependencies.get_file_service().resolve(proj, 'a.bin').read_bytes() == b'\x00\x01\x02'


@pytest.mark.anyio
async def test_delete_file(as_user, proj):
    as_user(EDITOR)
    assert await mcp.delete_file(proj, 'main.typ') == {'deleted': 'main.typ'}
    with pytest.raises(FileNotFoundError):
        await mcp.delete_file(proj, 'main.typ')


@pytest.mark.anyio
async def test_rename_file(as_user, proj):
    as_user(EDITOR)
    await mcp.rename_file(proj, 'main.typ', 'renamed.typ')
    assert mcp.read_file(proj, 'renamed.typ').startswith('= Hello')
    with pytest.raises(ValueError):
        await mcp.rename_file(proj, 'main.typ', 'x.typ')


@pytest.mark.anyio
async def test_directory_tools(as_user, proj):
    as_user(EDITOR)
    assert await mcp.create_dir(proj, 'd') == {'path': 'd'}
    with pytest.raises(ValueError):
        await mcp.create_dir(proj, 'd')

    await mcp.write_file(proj, 'd/x.typ', 'x')
    renamed = await mcp.rename_dir(proj, 'd', 'e')
    assert renamed['affected'] == ['d/x.typ']
    with pytest.raises(ValueError):
        await mcp.rename_dir(proj, 'd', 'f')

    deleted = await mcp.delete_dir(proj, 'e')
    assert deleted == {'deleted': 'e', 'affected': ['e/x.typ']}
    with pytest.raises(FileNotFoundError):
        await mcp.delete_dir(proj, 'e')


@pytest.mark.anyio
async def test_commit(as_user, proj):
    as_user(EDITOR)
    with pytest.raises(PermissionError):
        await mcp.commit(proj, 'msg')

    as_user(COMMIT)
    result = await mcp.commit(proj, 'all changes')
    assert result['message'] == 'all changes'
    assert 'co' in result['author']
    with pytest.raises(ValueError, match='Nothing to commit'):
        await mcp.commit(proj, 'again')


def test_commit_tool_registration_follows_config():
    names = {tool.name for tool in mcp.mcp._tool_manager.list_tools()}  # pylint: disable=protected-access
    assert ('commit' in names) is config.TINO_MCP_COMMIT_ENABLED
    assert {'list_buckets', 'read_file', 'write_file', 'write_binary_file', 'edit_file',
            'search', 'compile_typst'} <= names


# ── OIDCTokenVerifier ──

ISSUER = 'https://sso.example/realms/tino'


@pytest.fixture(scope='module')
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def verifier(rsa_key):
    v = mcp.OIDCTokenVerifier(f'{ISSUER}/.well-known/openid-configuration', 'groups')
    v._issuer = ISSUER  # pylint: disable=protected-access
    v._jwks_client = SimpleNamespace(  # pylint: disable=protected-access
        get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=rsa_key.public_key()),
    )
    return v


def _token(key, drop=(), **overrides):
    claims = {
        'iss': ISSUER, 'sub': 'u-1', 'preferred_username': 'alice', 'email': 'a@x',
        'groups': ['team'], 'azp': 'https://client.example/cimd', 'scope': 'openid email',
        'exp': int(time.time()) + 300,
    }
    claims.update(overrides)
    for claim in drop:
        claims.pop(claim)
    return jwt.encode(claims, key, algorithm='RS256')


@pytest.mark.anyio
async def test_verify_valid_token_binds_user(verifier, rsa_key):
    token = await verifier.verify_token(_token(rsa_key))
    assert token.client_id == 'https://client.example/cimd'
    assert token.scopes == ['openid', 'email']
    user = mcp._current_user.get()  # pylint: disable=protected-access
    assert (user.username, user.email, user.groups) == ('alice', 'a@x', ['team'])


@pytest.mark.anyio
async def test_verify_falls_back_to_sub(verifier, rsa_key):
    token = await verifier.verify_token(
        _token(rsa_key, drop=('preferred_username', 'groups', 'azp'), client_id='cid'))
    user = mcp._current_user.get()  # pylint: disable=protected-access
    assert user.username == 'u-1'
    assert user.groups == []
    assert token.client_id == 'cid'


@pytest.mark.anyio
@pytest.mark.parametrize('overrides', [
    {'exp': int(time.time()) - 10},
    {'iss': 'https://evil.example'},
])
async def test_verify_rejects_bad_claims(verifier, rsa_key, overrides):
    assert await verifier.verify_token(_token(rsa_key, **overrides)) is None


@pytest.mark.anyio
async def test_verify_rejects_foreign_signature(verifier):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert await verifier.verify_token(_token(other)) is None


@pytest.mark.anyio
async def test_verify_rejects_malformed(verifier):
    assert await verifier.verify_token('not-a-jwt') is None


@pytest.mark.anyio
async def test_verify_rejects_on_discovery_failure(rsa_key, monkeypatch):
    import httpx  # pylint: disable=import-outside-toplevel

    v = mcp.OIDCTokenVerifier('https://sso.invalid/.well-known/openid-configuration', 'groups')

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url, timeout):  # pylint: disable=unused-argument
            raise httpx.ConnectError('down')

    monkeypatch.setattr(mcp.httpx, 'AsyncClient', _Client)
    assert await v.verify_token(_token(rsa_key)) is None


@pytest.mark.anyio
async def test_dev_admin_middleware_injects_admin(monkeypatch):
    monkeypatch.setattr(config, 'TINO_ADMIN_GROUPS', {'admins'})
    seen = {}

    async def app(scope, receive, send):  # pylint: disable=unused-argument
        seen['user'] = mcp._current_user.get()  # pylint: disable=protected-access

    middleware = mcp._DevAdminMiddleware(app)  # pylint: disable=protected-access
    await middleware({'type': 'http'}, None, None)
    assert seen['user'].groups == ['admins']
    assert mcp._current_user.get() is None  # pylint: disable=protected-access

    await middleware({'type': 'lifespan'}, None, None)
    assert seen['user'] is None
