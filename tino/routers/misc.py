'''Health, config, theme, and well-known endpoints.'''

import logging
from importlib.metadata import PackageNotFoundError, version

import httpx
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse, Response

from .. import config
from ..services.compiler import CompilerService

logger = logging.getLogger(__name__)

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


@router.get('/.well-known/oauth-protected-resource')
async def oauth_protected_resource():
    '''RFC 9728 Protected Resource Metadata for MCP OAuth discovery.

    ``authorization_servers`` points to TINO itself (not directly to Keycloak)
    so that MCP clients fetch the proxied AS metadata from
    ``/.well-known/oauth-authorization-server`` below, which injects ``"none"``
    into ``token_endpoint_auth_methods_supported``.

    ``scopes_supported`` limits the scopes MCP clients request.  Without it,
    clients would request every scope from the AS metadata and Keycloak rejects
    the resulting superset as invalid.
    '''
    logger.debug('Protected resource metadata requested')
    if not config.TINO_MCP_ENABLED or not config.TINO_BASE_URL:
        reason = ('TINO_MCP_ENABLED is false'
                  if not config.TINO_MCP_ENABLED
                  else 'TINO_BASE_URL is empty')
        logger.warning('Protected resource metadata unavailable: %s', reason)
        return JSONResponse({'error': 'MCP not enabled'}, status_code=404)

    payload = {
        'resource': config.TINO_BASE_URL,
        'authorization_servers': [config.TINO_BASE_URL],
        'scopes_supported': ['openid', 'profile', 'email'],
        'bearer_methods_supported': ['header'],
    }
    logger.info('Protected resource metadata: resource=%s, AS=self',
                config.TINO_BASE_URL)
    return JSONResponse(payload)


@router.get('/.well-known/oauth-authorization-server')
async def oauth_authorization_server(request: Request):
    '''RFC 8414 Authorization Server Metadata proxy for MCP CIMD support.

    MCP clients such as Claude select
    `CIMD <https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/>`_
    over DCR only when the authorization server metadata advertises **both**:

    - ``client_id_metadata_document_supported: true``
    - ``"none"`` in ``token_endpoint_auth_methods_supported``

    Keycloak (tested up to 26.6.3, ``--features=cimd``) satisfies the first
    condition but **never** the second.  Internally, Keycloak builds the
    ``token_endpoint_auth_methods_supported`` list by iterating its registered
    ``ClientAuthenticator`` provider factories — none of which advertise
    ``"none"``.  The presence of public clients in the realm has no effect on
    the discovery document.

    This is a known upstream gap — see
    `keycloak#49730 <https://github.com/keycloak/keycloak/issues/49730>`_.
    This proxy is tracked as
    `tino#23 <https://github.com/confirm/tino/issues/23>`_
    and should be removed once the upstream fix ships.

    This endpoint proxies the provider's metadata and injects the missing value.
    All other fields — including ``authorization_endpoint``, ``token_endpoint``,
    and ``jwks_uri`` — are forwarded unchanged so the actual OAuth flow goes
    directly to Keycloak.

    The corresponding ``/.well-known/oauth-protected-resource`` endpoint lists
    TINO's own ``TINO_BASE_URL`` as the authorization server so that MCP clients
    discover this proxy rather than Keycloak's unpatched metadata.
    '''
    if not config.TINO_MCP_ENABLED or not config.TINO_OIDC_DISCOVERY_URL:
        return JSONResponse({'error': 'MCP not enabled'}, status_code=404)

    discovery = config.TINO_OIDC_DISCOVERY_URL
    try:
        resp = await request.app.state.http_client.get(discovery)
        resp.raise_for_status()
        meta = resp.json()
    except httpx.HTTPError as exc:
        logger.error('Failed to fetch AS metadata from %s: %s', discovery, exc)
        return JSONResponse({'error': 'upstream unavailable'}, status_code=502)

    # Keycloak omits "none" — inject it so MCP clients can select CIMD.
    # Safe because Keycloak *does* accept unauthenticated token requests for
    # public clients; it just doesn't advertise it in the discovery document.
    auth_methods = meta.get('token_endpoint_auth_methods_supported', [])
    if 'none' not in auth_methods:
        auth_methods.append('none')
        meta['token_endpoint_auth_methods_supported'] = auth_methods
        logger.debug('Injected "none" into token_endpoint_auth_methods_supported')

    return JSONResponse(meta)
