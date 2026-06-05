'''HTTP middleware for authentication enforcement.'''

import logging
import secrets

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from . import config

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
        '''Check session for authentication before forwarding the request.'''
        if config.TINO_AUTH_DISABLED:
            logger.debug('Auth disabled, skipping checks for %s %s',
                         request.method, request.url.path)
            return await call_next(request)

        path = request.url.path

        # The MCP resource endpoint validates its own OAuth bearer tokens.
        is_public = path in _PUBLIC_PATHS
        is_static = path.startswith(_STATIC_PREFIXES)
        is_mcp = path.startswith('/mcp')
        is_well_known = path.startswith('/.well-known/')
        if is_public or is_static or is_mcp or is_well_known:
            if is_mcp or is_well_known:
                logger.debug('MCP/well-known auth bypass: %s %s', request.method, path)
            else:
                logger.debug('Auth bypass for public/static path: %s', path)
            return await call_next(request)

        has_bearer = request.headers.get('Authorization', '').startswith('Bearer ')
        if has_bearer:
            logger.debug('Bearer token present on non-MCP path: %s %s',
                         request.method, path)
        if not request.session.get('user') and not has_bearer:
            if path.startswith('/api/'):
                logger.debug('Unauthenticated API request rejected (401): %s %s',
                             request.method, path)
                return JSONResponse({'detail': 'Not authenticated'}, status_code=401)

            logger.debug('Unauthenticated browser request redirected to login: %s', path)
            return RedirectResponse('/login')

        auth_method = 'Bearer token' if has_bearer else 'session cookie'
        logger.debug('Authenticated request forwarded: %s %s (%s)',
                     request.method, path, auth_method)
        return await call_next(request)


class _TrailingSlashMiddleware:  # pylint: disable=too-few-public-methods
    '''Append a trailing slash to ``/mcp`` so the Starlette Mount matches.

    Starlette's ``Mount('/mcp')`` compiles to a regex that requires at least
    ``/mcp/``.  Bare ``/mcp`` falls through to the static-files catch-all and
    returns 405.  This ASGI middleware rewrites the path in-place — no redirect.
    '''

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope.get('path') == '/mcp':
            scope['path'] = '/mcp/'
        await self.app(scope, receive, send)


def register_middleware(app: FastAPI) -> None:
    '''Attach session and auth middleware to the application.

    Middleware executes in reverse registration order, so auth runs first
    (registered last) and the session is available when it checks the cookie.
    '''
    app.add_middleware(AuthMiddleware)
    secret_key = config.TINO_SECRET_KEY or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret_key)
    app.add_middleware(_TrailingSlashMiddleware)
