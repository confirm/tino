'''HTTP middleware for authentication enforcement.'''

import logging
import secrets

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .auth import get_api_key_service

logger = logging.getLogger(__name__)

_PUBLIC_PATHS = {
    '/api/config',
    '/api/theme.css',
    '/health',
    '/login',
    '/oidc/login',
    '/oidc/callback',
    '/logout',
}

_STATIC_PREFIXES = (
    '/css/',
    '/js/',
    '/img/',
    '/favicon'
)


class AuthMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    '''Redirect unauthenticated requests to the login page (or return 401 for API calls).'''

    async def dispatch(self, request, call_next):
        '''Reject unauthenticated requests before forwarding to the route.'''
        if config.TINO_AUTH_DISABLED:
            logger.debug('Auth disabled, skipping checks for %s %s',
                         request.method, request.url.path)
            return await call_next(request)

        path = route_path(request.scope)

        # Public, static, MCP, and OAuth-discovery paths bypass the session gate.
        # MCP endpoints validate their own OAuth bearer tokens downstream.
        is_public = path in _PUBLIC_PATHS
        is_static = path.startswith(_STATIC_PREFIXES)
        is_mcp = path.startswith('/mcp')
        is_well_known = path.startswith('/.well-known/')
        if not (is_public or is_static or is_mcp or is_well_known):
            rejection = self._reject_if_unauthenticated(request, path)
            if rejection is not None:
                return rejection

        return await call_next(request)

    @staticmethod
    def _reject_if_unauthenticated(request, path):
        '''Return a 401/redirect response if the request lacks valid auth, else ``None``.

        The only valid bearer credential here is a static API key — MCP OAuth
        tokens target ``/mcp`` (bypassed above). The key is validated at the gate
        rather than trusting any ``Bearer`` header to reach a route dependency, so
        a route added without an auth dependency cannot be reached unauthenticated.
        '''
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            if get_api_key_service().verify(auth_header[7:]) is None:
                logger.warning('Invalid API key rejected: %s %s', request.method, path)
                return JSONResponse({'detail': 'Invalid API key'}, status_code=401)
            return None

        if request.session.get('user'):
            return None

        if path.startswith('/api/'):
            logger.debug('Unauthenticated API request rejected (401): %s %s',
                         request.method, path)
            return JSONResponse({'detail': 'Not authenticated'}, status_code=401)

        logger.debug('Unauthenticated browser request redirected to login: %s', path)
        return RedirectResponse(f'{config.TINO_ROOT_PATH}/login')


def route_path(scope) -> str:
    '''Return the request path below the ASGI ``root_path``.

    E.g. ``/login`` for ``/tino/login`` when TINO is served under ``/tino``.
    '''
    path = scope['path']
    root = scope.get('root_path', '')

    if root and (path == root or path.startswith(f'{root}/')):
        return path[len(root):] or '/'

    return path


class _RootPathMiddleware:  # pylint: disable=too-few-public-methods
    '''Serve TINO under :attr:`~tino.config.TINO_ROOT_PATH` (e.g. ``/tino``).

    Sets the ASGI ``root_path``, so Starlette routes on the path below the
    prefix. Requests arrive either with the prefix (the proxy passes the path
    through) or without it (the proxy strips it); the latter get the prefix
    prepended, so both look the same to the app. The bare prefix is redirected
    to ``prefix/``, so the frontend's relative URLs resolve below it.
    '''

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        root = config.TINO_ROOT_PATH

        if not root or scope['type'] not in ('http', 'websocket'):
            await self.app(scope, receive, send)
            return

        path = scope['path']

        if path == root and scope['type'] == 'http':
            query = scope.get('query_string', b'').decode('latin-1')
            location = f'{root}/?{query}' if query else f'{root}/'
            await RedirectResponse(location)(scope, receive, send)
            return

        scope = {**scope, 'root_path': root}

        if not path.startswith(f'{root}/'):
            scope['path'] = root + path
            if 'raw_path' in scope:
                scope['raw_path'] = root.encode('ascii') + scope['raw_path']

        await self.app(scope, receive, send)


class _TrailingSlashMiddleware:  # pylint: disable=too-few-public-methods
    '''Append a trailing slash to ``/mcp`` so the Starlette Mount matches.

    Starlette's ``Mount('/mcp')`` compiles to a regex that requires at least
    ``/mcp/``.  Bare ``/mcp`` falls through to the static-files catch-all and
    returns 405.  This ASGI middleware rewrites the path in-place — no redirect.
    '''

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and route_path(scope) == '/mcp':
            scope['path'] += '/'
        await self.app(scope, receive, send)


def register_middleware(app: FastAPI) -> None:
    '''Attach session and auth middleware to the application.

    Middleware executes in reverse registration order, so auth runs first
    (registered last) and the session is available when it checks the cookie.
    '''
    app.add_middleware(AuthMiddleware)
    secret_key = config.TINO_SECRET_KEY or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret_key,
                       path=config.TINO_ROOT_PATH or '/')
    app.add_middleware(_TrailingSlashMiddleware)
    # Compress responses — the SVG preview ships as verbose text and shrinks
    # ~5-10x over the wire, which dominates load time on slow connections.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    # Outermost, so every other middleware already sees the sub-path root_path.
    app.add_middleware(_RootPathMiddleware)
