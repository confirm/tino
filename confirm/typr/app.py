'''FastAPI application factory. Mounts routers, WebSocket collab, and static frontend.'''

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import config
from .auth import check_access
from .auth import router as auth_router
from .auth import setup_oauth
from .dependencies import get_bucket_service, get_collab_manager
from .models import User
from .routers import buckets
from .routers import compile as compile_router
from .routers import files, git, templates

_STATIC_DIR = str(Path(__file__).parent / 'static')

_PUBLIC_PATHS = {'/login', '/oidc/login', '/oidc-callback', '/logout'}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    '''Ensure the data directory exists on startup and flush collab rooms on shutdown.'''
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    config.sanity_checks()
    await setup_oauth()
    collab = get_collab_manager()
    collab.start()
    yield
    await collab.shutdown()


def _is_static(path: str) -> bool:
    '''Check if the path is for a static asset.'''
    return path.startswith(('/css/', '/js/', '/img/', '/favicon'))


def create_app() -> FastAPI:
    '''Create and return the Typr FastAPI application.'''
    app = FastAPI(title='Typr', lifespan=lifespan)

    app.include_router(auth_router)
    app.include_router(buckets.router)
    app.include_router(compile_router.router)
    app.include_router(files.router)
    app.include_router(git.router)
    app.include_router(templates.router)

    @app.middleware('http')
    async def require_auth(request: Request, call_next):
        '''Enforce authentication on all routes except public and static ones.'''
        path = request.url.path
        if path in _PUBLIC_PATHS or _is_static(path):
            return await call_next(request)

        if not request.session.get('user'):
            if path.startswith('/api/'):
                return JSONResponse({'detail': 'Not authenticated'}, status_code=401)
            return RedirectResponse('/login')

        return await call_next(request)

    secret_key = config.SECRET_KEY or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret_key)

    @app.websocket('/api/buckets/{slug}/collab/{path:path}')
    async def collab_websocket(websocket: WebSocket, slug: str, path: str):
        '''Yjs WebSocket endpoint for real-time collaborative editing of a file.'''
        user_data = websocket.session.get('user')
        if not user_data:
            await websocket.close(code=4401, reason='Not authenticated')
            return

        user = User(**user_data)
        bucket_svc = get_bucket_service()
        bucket = bucket_svc.get(slug)
        if not bucket:
            await websocket.close(code=4004, reason='Bucket not found')
            return
        try:
            check_access(user, bucket.access, 'editor')
        except HTTPException:
            await websocket.close(code=4403, reason='Editor role required')
            return

        collab = get_collab_manager()
        await collab.serve(websocket, slug, path)

    app.mount('/', StaticFiles(directory=_STATIC_DIR, html=True), name='frontend')

    return app
