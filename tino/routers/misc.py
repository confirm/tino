'''Health, config, and theme endpoints.'''

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter
from starlette.responses import Response

from .. import config
from ..services.compiler import CompilerService

router = APIRouter(tags=['misc'])


def _app_version() -> str:
    try:
        return version('tino')
    except PackageNotFoundError:
        return 'unknown'


def _typst_version() -> str | None:
    try:
        return CompilerService.version()
    except Exception:  # pylint: disable=broad-exception-caught
        return None


def _count_buckets() -> int:
    if not config.TINO_BUCKET_DIR.is_dir():
        return 0
    return sum(
        1 for entry in config.TINO_BUCKET_DIR.iterdir()
        if entry.is_dir() and (entry / '.git').is_dir()
    )


_APP_VERSION = _app_version()
_TYPST_VERSION = _typst_version()


@router.get('/health')
async def health():
    '''Basic health check with version info and bucket count.'''
    return {
        'status': 'ok',
        'version': _APP_VERSION,
        'typst': _TYPST_VERSION,
        'buckets': _count_buckets(),
    }


@router.get('/api/config')
async def frontend_config():
    '''Return frontend configuration values.'''
    return {
        'saveDebounceMs': config.TINO_SAVE_DEBOUNCE_MS,
        'version': _APP_VERSION,
    }


@router.get('/api/theme.css')
async def theme_css():
    '''Return CSS custom properties for the configured accent colour family.'''
    colour = config.TINO_ACCENT_COLOUR
    css = (
        ':root{'
        f'--accent-50:var(--cd-{colour}-50);'
        f'--accent-60:var(--cd-{colour}-60);'
        f'--accent-70:var(--cd-{colour}-70);'
        f'--logo-main-colour:var(--cd-{colour}-60);'
        f'--logo-accent-colour:var(--cd-{colour}-80)'
        '}\n'
    )
    return Response(content=css, media_type='text/css')
