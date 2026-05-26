'''FastAPI application factory. Mounts routers, WebSocket collab, and static frontend.'''

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .auth import router as auth_router
from .auth import setup_oauth
from .dependencies import get_collab_manager
from .middleware import register_middleware
from .routers import buckets, collab
from .routers import compile as compile_router
from .routers import files, git, templates

_STATIC_DIR = str(Path(__file__).parent / 'static')


@asynccontextmanager
async def lifespan(_app: FastAPI):
    '''Ensure the data directory exists on startup and flush collab rooms on shutdown.'''
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    config.sanity_checks()
    await setup_oauth()
    collab_mgr = get_collab_manager()
    collab_mgr.start()
    yield
    await collab_mgr.shutdown()


def create_app() -> FastAPI:
    '''Create and return the Typr FastAPI application.'''
    app = FastAPI(title='Typr', lifespan=lifespan)

    app.include_router(auth_router)
    app.include_router(buckets.router)
    app.include_router(collab.router)
    app.include_router(compile_router.router)
    app.include_router(files.router)
    app.include_router(git.router)
    app.include_router(templates.router)

    register_middleware(app)

    app.mount('/', StaticFiles(directory=_STATIC_DIR, html=True), name='frontend')

    return app
