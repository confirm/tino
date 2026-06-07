'''MCP (Model Context Protocol) server exposing TINO as tools for AI agents.

The server is mounted into the main FastAPI app as a Streamable HTTP ASGI
sub-application at ``/mcp``. It reuses TINO's existing services and enforces the
same per-bucket role model as the REST API.

Authentication follows the MCP OAuth 2.0 specification: TINO acts as a *Resource
Server* and delegates authentication to the configured OIDC provider (it still
enforces its own per-bucket authorization). MCP clients
identify themselves to that provider with a `Client ID Metadata Document
<https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/>`_
(CIMD) — their ``client_id`` is an HTTPS URL the provider dereferences, so there is
no Dynamic Client Registration — obtain an access token, and present it to TINO as a
Bearer token. TINO validates the token against the provider's JWKS and runs each
tool as that user, with their real group memberships driving bucket access.
'''

import logging
from contextvars import ContextVar
from urllib.parse import urlparse

import anyio
import httpx
import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import config
from .auth import ROLE_HIERARCHY, resolve_role
from .dependencies import get_bucket_service, get_collab_manager, get_compiler_service, \
    get_file_service, get_git_service, get_notifier
from .models import User

logger = logging.getLogger(__name__)

#: The authenticated user for the in-flight MCP request.
_current_user: ContextVar[User | None] = ContextVar('mcp_user', default=None)

_DISCOVERY_SUFFIX = '/.well-known/openid-configuration'

_INSTRUCTIONS = '''\
TINO is a collaborative Typst document platform. Documents live in *buckets*
(git repositories). Use these tools to list, read, write, compile, and commit
Typst source files. Always compile after editing to verify the document is valid.
Each bucket may have specific instructions — always list buckets first and follow
any per-bucket guidance.
'''

if config.TINO_MCP_INSTRUCTIONS:
    _INSTRUCTIONS += '\n' + config.TINO_MCP_INSTRUCTIONS + '\n'


def _issuer_url(discovery_url: str) -> str:
    '''Derive the OAuth issuer URL from the OIDC discovery URL.'''
    if discovery_url.endswith(_DISCOVERY_SUFFIX):
        return discovery_url[:-len(_DISCOVERY_SUFFIX)]
    return discovery_url


# ── Authentication (OAuth Resource Server) ──


class OIDCTokenVerifier(TokenVerifier):  # pylint: disable=too-few-public-methods
    '''Validate provider-issued JWT access tokens against the OIDC JWKS.

    On success the token's claims are turned into a :class:`~tino.models.User`
    (username + groups) and bound to the request context for the tools to use.
    '''

    def __init__(self, discovery_url: str, groups_claim: str) -> None:
        self._discovery_url = discovery_url
        self._groups_claim = groups_claim
        self._issuer: str | None = None
        self._jwks_client: jwt.PyJWKClient | None = None
        self._lock = anyio.Lock()
        logger.debug(
            'OIDCTokenVerifier configured: discovery=%s, groups_claim=%s',
            discovery_url, groups_claim,
        )

    async def _ensure_metadata(self) -> None:
        '''Lazily fetch the issuer and JWKS URI from the discovery document.'''
        if self._jwks_client is not None:
            return
        async with self._lock:
            if self._jwks_client is not None:
                return
            logger.debug('Fetching OIDC discovery from %s', self._discovery_url)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(self._discovery_url, timeout=10)
                    resp.raise_for_status()
                    meta = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    'OIDC discovery failed: url=%s, status=%d',
                    self._discovery_url, exc.response.status_code,
                )
                raise
            except httpx.HTTPError as exc:
                logger.error(
                    'OIDC discovery network error: url=%s, error=%s',
                    self._discovery_url, exc,
                )
                raise
            self._issuer = meta['issuer']
            self._jwks_client = jwt.PyJWKClient(meta['jwks_uri'])
            logger.info(
                'OIDC metadata loaded: issuer=%s, jwks_uri=%s',
                self._issuer, meta['jwks_uri'],
            )

    @staticmethod
    def _safe_claims(token: str) -> dict:
        '''Decode the JWT payload without verification for diagnostic logging.'''
        try:
            return jwt.decode(token, options={
                'verify_signature': False,
                'verify_exp': False,
                'verify_iss': False,
                'verify_aud': False,
            })
        except Exception:  # pylint: disable=broad-exception-caught
            return {}

    async def verify_token(self, token: str) -> AccessToken | None:
        '''Validate the JWT and bind the resolved user to the request context.'''
        logger.debug('Verifying MCP bearer token (%d chars)', len(token))
        try:
            await self._ensure_metadata()
            signing_key = await anyio.to_thread.run_sync(
                self._jwks_client.get_signing_key_from_jwt, token,
            )
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                issuer=self._issuer,
                # Signature, issuer and expiry are validated, but NOT the
                # audience: Keycloak issues CIMD-flow tokens with no ``aud`` claim
                # (the ephemeral client has no registered entry to carry an
                # audience mapper), so there is nothing to bind to. A token issued
                # to another client in the same realm is therefore accepted here
                # and constrained only by per-bucket authorization. See ADR-10
                # and tino#24; enable verify_aud once the provider sets ``aud``.
                options={'verify_aud': False},
            )
        except jwt.ExpiredSignatureError as exc:
            unverified = self._safe_claims(token)
            logger.warning(
                'MCP token rejected (expired): %s (iss=%s, exp=%s, azp=%s)',
                exc, unverified.get('iss'), unverified.get('exp'),
                unverified.get('azp'),
            )
            return None
        except jwt.InvalidIssuerError as exc:
            unverified = self._safe_claims(token)
            logger.warning(
                'MCP token rejected (issuer mismatch, expected=%s): %s'
                ' (iss=%s, exp=%s, azp=%s)',
                self._issuer, exc, unverified.get('iss'),
                unverified.get('exp'), unverified.get('azp'),
            )
            return None
        except jwt.InvalidSignatureError as exc:
            unverified = self._safe_claims(token)
            logger.warning(
                'MCP token rejected (bad signature): %s (iss=%s, exp=%s, azp=%s)',
                exc, unverified.get('iss'), unverified.get('exp'),
                unverified.get('azp'),
            )
            return None
        except jwt.DecodeError as exc:
            logger.warning('MCP token rejected (malformed JWT): %s', exc)
            return None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Network errors, JWKS fetch failures, or anything else.
            is_network = isinstance(exc, (httpx.HTTPError, OSError))
            reason = 'network/JWKS' if is_network else type(exc).__name__
            logger.warning('MCP token rejected (%s): %s', reason, exc)
            return None

        user = User(
            username=claims.get('preferred_username', claims.get('sub', '')),
            email=claims.get('email', ''),
            groups=claims.get(self._groups_claim) or [],
        )
        _current_user.set(user)
        logger.info('MCP authenticated user: %s', user.username)
        # ``aud``/``azp``/``client_id`` are logged for auth diagnostics. Keycloak
        # CIMD tokens carry no ``aud`` (see the ``verify_aud`` note above); ``azp``
        # holds the client's CIMD URL. ``aud`` uses %r as it may be a string or list.
        logger.debug(
            'MCP token details: user=%s, email=%s, groups=%s, iss=%s, exp=%s, '
            'aud=%r, azp=%s, client_id=%s',
            user.username, user.email, user.groups,
            claims.get('iss'), claims.get('exp'),
            claims.get('aud'), claims.get('azp'), claims.get('client_id'),
        )

        return AccessToken(
            token=token,
            client_id=claims.get('azp') or claims.get('client_id', ''),
            scopes=claims.get('scope', '').split(),
            expires_at=claims.get('exp'),
        )


def _noauth_user() -> User:
    '''Build the implicit admin user used when ``TINO_AUTH_DISABLED`` is set.'''
    return User(username='tino', email='tino@localhost', groups=list(config.TINO_ADMIN_GROUPS))


class _DevAdminMiddleware:  # pylint: disable=too-few-public-methods
    '''Inject an implicit admin user when ``TINO_AUTH_DISABLED`` is set (dev only).'''

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        user = _noauth_user()
        logger.debug('DevAdminMiddleware injecting implicit admin: %s', user.username)
        token = _current_user.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_user.reset(token)


def _build_auth_kwargs() -> dict:
    '''Return the FastMCP auth kwargs, or an empty dict when auth is disabled.'''
    if config.TINO_AUTH_DISABLED:
        logger.info('MCP auth disabled (TINO_AUTH_DISABLED)')
        return {}
    if not (config.TINO_OIDC_DISCOVERY_URL and config.TINO_BASE_URL):
        logger.warning('MCP auth not configured (missing OIDC_DISCOVERY_URL or BASE_URL)')
        return {}
    issuer = _issuer_url(config.TINO_OIDC_DISCOVERY_URL)
    resource_url = f'{config.TINO_BASE_URL}/mcp'
    logger.info('MCP auth: issuer=%s, resource=%s', issuer, resource_url)
    return {
        'token_verifier': OIDCTokenVerifier(
            config.TINO_OIDC_DISCOVERY_URL, config.TINO_OIDC_GROUPS_CLAIM,
        ),
        'auth': AuthSettings(
            issuer_url=issuer,
            resource_server_url=resource_url,
            required_scopes=[],
        ),
    }


_auth_kwargs = _build_auth_kwargs()

# Allow the configured base URL host (plus localhost for dev).
_allowed_hosts = ['localhost:*', '127.0.0.1:*']
if config.TINO_BASE_URL:
    _allowed_hosts.append(urlparse(config.TINO_BASE_URL).netloc)
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=_allowed_hosts,
)

mcp = FastMCP(
    'TINO',
    instructions=_INSTRUCTIONS,
    stateless_http=True,
    json_response=True,
    # The handler sits at the sub-app root; the app mounts it under /mcp.
    streamable_http_path='/',
    transport_security=_transport_security,
    **_auth_kwargs,
)
logger.info(
    'FastMCP instance created: stateless_http=True, auth_configured=%s',
    'token_verifier' in _auth_kwargs,
)


# ── Authorization helpers ──


def _require(slug: str, min_role: str) -> User:
    '''Resolve the current user and enforce *min_role* on *slug*.

    Returns the resolved ``User``. Raises ``PermissionError`` if the user lacks
    the role, or ``FileNotFoundError`` if the bucket does not exist.
    '''
    user = _current_user.get()
    if user is None:
        raise PermissionError('Not authenticated')

    bucket = get_bucket_service().get(slug)
    if bucket is None:
        raise FileNotFoundError(f'Bucket not found: {slug}')

    role = resolve_role(user, bucket.access, slug)
    if role is None or ROLE_HIERARCHY[role] < ROLE_HIERARCHY[min_role]:
        logger.warning(
            'MCP authorization denied: user=%s, bucket=%s, required=%s, actual=%s',
            user.username, slug, min_role, role,
        )
        raise PermissionError(f"'{min_role}' role required for bucket '{slug}'")

    logger.debug(
        'MCP authorization granted: user=%s, bucket=%s, role=%s',
        user.username, slug, role,
    )
    return user


# ── Tools ──


@mcp.tool()
def list_buckets() -> list[dict]:
    '''List all buckets the current user can access, with their role on each.

    Buckets may include an ``instructions`` field with specific guidance for
    working with that bucket's content.  Always read and follow these
    instructions before making changes.
    '''
    user = _current_user.get()
    if user is None:
        raise PermissionError('Not authenticated')

    logger.debug('MCP list_buckets called by user=%s', user.username)
    results = []
    for bucket in get_bucket_service().list():
        role = resolve_role(user, bucket.access, bucket.slug)
        if role is not None:
            entry = {
                'slug': bucket.slug,
                'description': bucket.description,
                'role': role,
            }
            if bucket.mcp_instructions:
                entry['instructions'] = bucket.mcp_instructions
            results.append(entry)
    logger.debug('MCP list_buckets returning %d buckets for user=%s', len(results), user.username)
    return results


@mcp.tool()
def list_files(bucket: str) -> list[dict]:
    '''List all files and directories in a bucket.'''
    logger.debug('MCP list_files called: bucket=%s', bucket)
    _require(bucket, 'viewer')
    return [entry.model_dump() for entry in get_file_service().list(bucket)]


@mcp.tool()
def read_file(bucket: str, path: str) -> str:
    '''Read the text content of a file in a bucket.'''
    logger.debug('MCP read_file called: bucket=%s, path=%s', bucket, path)
    _require(bucket, 'viewer')

    # If the file is open in the web UI, return the live collab-room content so
    # reads reflect unsaved edits rather than the (older) on-disk copy.
    live = get_collab_manager().get_content(bucket, path)
    if live is not None:
        return live

    result = get_file_service().read(bucket, path)
    if result is None:
        raise FileNotFoundError(f'File not found: {bucket}/{path}')
    if result.get('binary'):
        raise ValueError(f'File is binary and cannot be read as text: {bucket}/{path}')

    return result['content']


@mcp.tool()
async def write_file(bucket: str, path: str, content: str) -> dict:
    '''Create or overwrite a text file in a bucket. Requires the editor role.'''
    user = _require(bucket, 'editor')
    modified = get_file_service().write(bucket, path, content)

    if modified is None:
        raise ValueError(f'Invalid path: {path}')

    # Push the new content into any open collab room so connected web-UI clients
    # see it, and the room's eventual flush doesn't overwrite this write.
    await get_collab_manager().reload_rooms(bucket, [path])
    logger.info('MCP wrote %s/%s (user: %s)', bucket, path, user.username)
    await get_notifier().notify(bucket)
    return {'path': path, 'modified': modified}


@mcp.tool()
async def delete_file(bucket: str, path: str) -> dict:
    '''Delete a file from a bucket. Requires the editor role.'''
    user = _require(bucket, 'editor')

    # Evict any open collab room (without flushing) around the delete, so a
    # pending flush can't re-create the file the tool just removed.
    async with get_collab_manager().lock_path(bucket, path):
        if not get_file_service().delete(bucket, path):
            raise FileNotFoundError(f'File not found: {bucket}/{path}')

    logger.info('MCP deleted %s/%s (user: %s)', bucket, path, user.username)
    await get_notifier().notify(bucket)
    return {'deleted': path}


@mcp.tool()
async def rename_file(bucket: str, old_path: str, new_path: str) -> dict:
    '''Rename or move a file within a bucket. Requires the editor role.

    Fails if the source is missing, the destination already exists, or the path
    is invalid.
    '''
    user = _require(bucket, 'editor')

    # Evict any open collab room for the source (without flushing) so a pending
    # flush can't re-create the file at its old path after the move.
    async with get_collab_manager().lock_path(bucket, old_path):
        if not get_file_service().rename(bucket, old_path, new_path):
            raise ValueError(
                f'Invalid path or target exists: {old_path} -> {new_path}')

    logger.info('MCP renamed %s/%s -> %s (user: %s)',
                bucket, old_path, new_path, user.username)
    await get_notifier().notify(bucket)
    return {'old_path': old_path, 'new_path': new_path}


@mcp.tool()
async def create_dir(bucket: str, path: str) -> dict:
    '''Create an empty directory in a bucket. Requires the editor role.

    Fails if the directory already exists or the path is invalid.  Note that git
    does not track empty directories, so a created directory only persists once
    it contains a committed file.
    '''
    user = _require(bucket, 'editor')

    if not get_file_service().create_dir(bucket, path):
        raise ValueError(f'Directory already exists or invalid path: {path}')

    logger.info('MCP created dir %s/%s (user: %s)', bucket, path, user.username)
    await get_notifier().notify(bucket)
    return {'path': path}


@mcp.tool()
async def rename_dir(bucket: str, old_path: str, new_path: str) -> dict:
    '''Rename or move a directory and all its contents. Requires the editor role.'''
    user = _require(bucket, 'editor')

    # Evict any open collab rooms under the directory before moving it.
    await get_collab_manager().evict_under(bucket, old_path)
    affected = get_file_service().rename_dir(bucket, old_path, new_path)

    if affected is None:
        raise ValueError(
            f'Invalid path or target exists: {old_path} -> {new_path}')

    logger.info('MCP renamed dir %s/%s -> %s (user: %s)',
                bucket, old_path, new_path, user.username)
    await get_notifier().notify(bucket)
    return {'old_path': old_path, 'new_path': new_path, 'affected': affected}


@mcp.tool()
async def delete_dir(bucket: str, path: str) -> dict:
    '''Delete a directory and all its contents. Requires the editor role.'''
    user = _require(bucket, 'editor')

    # Evict any open collab rooms under the directory before deleting it.
    await get_collab_manager().evict_under(bucket, path)
    affected = get_file_service().delete_dir(bucket, path)

    if affected is None:
        raise FileNotFoundError(f'Directory not found: {bucket}/{path}')

    logger.info('MCP deleted dir %s/%s (%d files) (user: %s)',
                bucket, path, len(affected), user.username)
    await get_notifier().notify(bucket)
    return {'deleted': path, 'affected': affected}


@mcp.tool()
def compile_typst(bucket: str, path: str) -> dict:
    '''Compile a Typst file to verify it is valid.

    Returns ``{"success": true, "pages": N}`` when compilation succeeds, or
    ``{"success": false, "error": "..."}`` with the compiler error otherwise.
    Use this after editing to check your work before committing.
    '''
    logger.debug('MCP compile_typst called: bucket=%s, path=%s', bucket, path)
    _require(bucket, 'viewer')

    try:
        pages = get_compiler_service().compile_svg(bucket, path)
        return {'success': True, 'pages': len(pages)}
    except FileNotFoundError as exc:
        raise FileNotFoundError(str(exc)) from exc
    except RuntimeError as exc:
        return {'success': False, 'error': str(exc)}


@mcp.tool()
def git_status(bucket: str) -> list[dict]:
    '''Return the working-tree status (modified, untracked, deleted) of a bucket.'''
    logger.debug('MCP git_status called: bucket=%s', bucket)
    _require(bucket, 'viewer')
    return [s.model_dump() for s in get_git_service().status(bucket)]


@mcp.tool()
def git_log(bucket: str, path: str | None = None, max_count: int = 20) -> list[dict]:
    '''Return commit history for a bucket, optionally filtered to a single file.'''
    logger.debug('MCP git_log called: bucket=%s, path=%s', bucket, path)
    _require(bucket, 'viewer')
    commits = get_git_service().log(bucket, path, max_count=max_count)
    return [c.model_dump() for c in commits]


@mcp.tool()
async def commit(bucket: str, message: str, files: list[str] | None = None) -> dict:
    '''Commit changes in a bucket. Requires the committer role.

    If *files* is omitted, all changed files in the working tree are committed.
    '''
    user = _require(bucket, 'committer')

    if files is None:
        files = [s.path for s in get_git_service().status(bucket)]

    if not files:
        raise ValueError('Nothing to commit')

    result = get_git_service().commit(
        bucket, files, message, author=user.username, email=user.email,
    )
    logger.info('MCP committed %s: %r (user: %s)', bucket, message, user.username)
    await get_notifier().notify(bucket)
    return result.model_dump()


# Build the ASGI app once. In dev (auth disabled) an admin user is injected;
# otherwise the OAuth resource-server machinery enforces authentication.
_base_app = mcp.streamable_http_app()
if config.TINO_AUTH_DISABLED:
    mcp_asgi_app = _DevAdminMiddleware(_base_app)
    logger.info('MCP ASGI app built with DevAdminMiddleware (auth disabled)')
else:
    mcp_asgi_app = _base_app
    logger.info('MCP ASGI app built with OAuth token verification')
