'''FastAPI application factory. Mounts routers, WebSocket collab, and static frontend.'''

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .auth import router as auth_router
from .auth import setup_oauth
from .dependencies import get_collab_manager
from .middleware import register_middleware
from .routers import api_keys, buckets, collab
from .routers import compile as compile_router
from .routers import events, files, fonts, git, misc, templates

logger = logging.getLogger(__name__)

_STATIC_DIR = str(Path(__file__).parent / 'static')


@asynccontextmanager
async def lifespan(_app: FastAPI):
    '''Ensure the data directory exists on startup and flush collab rooms on shutdown.'''
    # Suppress noisy loggers after uvicorn has finished configuring its own logging.
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)

    config.TINO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.TINO_BUCKET_DIR.mkdir(parents=True, exist_ok=True)
    config.TINO_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    config.TINO_FONT_DIR.mkdir(parents=True, exist_ok=True)

    config.sanity_checks()

    if not config.TINO_AUTH_DISABLED:
        await setup_oauth()

    collab_mgr = get_collab_manager()
    collab_mgr.start()

    yield

    await collab_mgr.shutdown()


def create_app() -> FastAPI:
    '''Create and return the TINO FastAPI application.'''
    logging.basicConfig(
        level=config.TINO_LOG_LEVEL,
        format='%(levelname)-8s %(name)s  %(message)s',
    )
    logging.getLogger('git').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('pycrdt').setLevel(logging.WARNING)

    app = FastAPI(title='TINO', lifespan=lifespan)

    app.include_router(auth_router)
    app.include_router(misc.router)
    app.include_router(api_keys.router)
    app.include_router(buckets.router)
    app.include_router(collab.router)
    app.include_router(compile_router.router)
    app.include_router(events.router)
    app.include_router(files.router)
    app.include_router(fonts.router)
    app.include_router(git.router)
    app.include_router(templates.router)

    register_middleware(app)

    app.mount('/', StaticFiles(directory=_STATIC_DIR, html=True), name='frontend')

    return app
