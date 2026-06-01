'''FastAPI application factory. Mounts routers, WebSocket collab, and static frontend.'''

import logging
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
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
from .routers import events, files, fonts, git, templates
from .services.compiler import CompilerService

logger = logging.getLogger(__name__)

_STATIC_DIR = str(Path(__file__).parent / 'static')


def _resolve_app_version() -> str:
    '''Look up the installed TINO package version, or "unknown" if unavailable.'''
    try:
        return version('tino')
    except PackageNotFoundError:
        return 'unknown'


def _resolve_typst_version() -> str | None:
    '''Probe the Typst CLI once; returns None if the binary is missing or fails.'''
    try:
        return CompilerService.version()
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning('Typst CLI not available; /health will report typst=null')
        return None


def _count_buckets() -> int:
    '''Cheap bucket count: directories under TINO_BUCKET_DIR with a .git folder.'''
    if not config.TINO_BUCKET_DIR.is_dir():
        return 0
    return sum(
        1 for entry in config.TINO_BUCKET_DIR.iterdir()
        if entry.is_dir() and (entry / '.git').is_dir()
    )


_APP_VERSION = _resolve_app_version()
_TYPST_VERSION = _resolve_typst_version()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    '''Ensure the data directory exists on startup and flush collab rooms on shutdown.'''
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
        format='%(asctime)s %(levelname)-8s %(name)s  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logging.getLogger('git').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('pycrdt').setLevel(logging.WARNING)

    app = FastAPI(title='TINO', lifespan=lifespan)

    @app.get('/health')
    async def health():
        return {
            'status': 'ok',
            'version': _APP_VERSION,
            'typst': _TYPST_VERSION,
            'buckets': _count_buckets(),
        }

    @app.get('/api/config')
    async def frontend_config():
        return {
            'saveDebounceMs': config.TINO_SAVE_DEBOUNCE_MS,
            'version': _APP_VERSION,
        }

    app.include_router(auth_router)
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
