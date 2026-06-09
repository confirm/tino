'''FastAPI application factory. Mounts routers, WebSocket collab, and static frontend.'''

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .auth import router as auth_router
from .auth import setup_oauth
from .dependencies import get_collab_manager
from .mcp.server import mcp as mcp_server
from .mcp.server import mcp_asgi_app
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
        logger.info('OAuth setup complete')

    collab_mgr = get_collab_manager()
    collab_mgr.start()

    # One shared HTTP client for TINO's outbound calls (the MCP discovery proxy),
    # reused across requests instead of constructed per call.
    _app.state.http_client = httpx.AsyncClient(timeout=10)

    if config.TINO_MCP_ENABLED:
        logger.info('MCP server enabled, starting session manager')
        # The MCP Streamable HTTP session manager must run for the lifetime of
        # the app. Mounted sub-apps don't get their lifespan invoked, so we run
        # it here within TINO's own lifespan.
        async with mcp_server.session_manager.run():
            logger.info('MCP session manager started')
            yield
            logger.info('MCP session manager shutting down')
    else:
        logger.debug('MCP server disabled')
        yield

    await _app.state.http_client.aclose()
    await collab_mgr.shutdown()


def create_app() -> FastAPI:
    '''Create and return the TINO FastAPI application.'''
    logging.basicConfig(
        level=config.TINO_LOG_LEVEL,
        format='%(levelname)-8s %(name)s  %(message)s',
        force=True,
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

    if config.TINO_MCP_ENABLED:
        auth_mode = 'no-auth' if config.TINO_AUTH_DISABLED else 'OAuth'
        logger.info('Mounting MCP sub-app at /mcp (auth_mode=%s)', auth_mode)
        app.mount('/mcp', mcp_asgi_app, name='mcp')
    else:
        logger.debug('MCP endpoint not mounted (TINO_MCP_ENABLED is false)')

    app.mount('/', StaticFiles(directory=_STATIC_DIR, html=True), name='frontend')

    return app
