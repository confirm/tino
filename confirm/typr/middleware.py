'''HTTP middleware for authentication enforcement.'''

import secrets

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from . import config

_PUBLIC_PATHS = {
    '/login',
    '/oidc/login',
    '/oidc-callback',
    '/logout'
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
        path = request.url.path

        if path in _PUBLIC_PATHS or path.startswith(_STATIC_PREFIXES):
            return await call_next(request)

        if not request.session.get('user'):
            if path.startswith('/api/'):
                return JSONResponse({'detail': 'Not authenticated'}, status_code=401)

            return RedirectResponse('/login')

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    '''Attach session and auth middleware to the application.

    Middleware executes in reverse registration order, so auth runs first
    (registered last) and the session is available when it checks the cookie.
    '''
    app.add_middleware(AuthMiddleware)
    secret_key = config.SECRET_KEY or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret_key)
