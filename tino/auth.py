'''OIDC authentication and role-based access control.'''

from logging import getLogger
from pathlib import Path

import yaml
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse

from . import config
from .models import AccessEntry, User
from .services.api_keys import ApiKeyService

logger = getLogger(__name__)

_LOGIN_HTML = str(Path(__file__).resolve().parent / 'static' / 'login.html')

router = APIRouter(tags=['auth'])

oauth = OAuth()

ROLE_HIERARCHY = {'viewer': 0, 'editor': 1, 'committer': 2}

_api_key_service = ApiKeyService(config.TINO_DATA_DIR / 'api_keys.yml')


def get_api_key_service() -> ApiKeyService:
    '''Return the global :class:`~tino.services.api_keys.ApiKeyService` instance.'''
    return _api_key_service


# ── Authentication ──


async def setup_oauth():
    '''Register the OIDC provider with authlib and pre-fetch discovery metadata.'''
    logger.info('Registering OIDC provider: %s', config.TINO_OIDC_DISCOVERY_URL)
    oauth.register(
        name='oidc',
        client_id=config.TINO_OIDC_CLIENT_ID,
        client_secret=config.TINO_OIDC_CLIENT_SECRET,
        server_metadata_url=config.TINO_OIDC_DISCOVERY_URL,
        client_kwargs={},
    )
    scopes = ['openid', 'email', 'profile']

    await oauth.oidc.load_server_metadata()
    metadata = oauth.oidc.server_metadata

    if config.TINO_LOCAL_GROUPS:
        logger.info(
            'TINO_LOCAL_GROUPS is enabled. '
            'Relying on YAML for groups, and omitting OIDC groups scope.')
    else:
        # Some providers omit 'scopes_supported' entirely, so we check if the key exists first
        supported_scopes = metadata.get('scopes_supported')

        if supported_scopes is not None and 'groups' not in supported_scopes:
            error_msg = (
                "Your OIDC provider does not support the 'groups' scope, which TINO "
                "requires for group-based access control. Set TINO_LOCAL_GROUPS=true and map "
                "user emails to groups in .groups.yml."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        scopes.append('groups')

    oauth.oidc.client_kwargs['scope'] = ' '.join(scopes)

    logger.info('OIDC provider ready (client_id=%s)', config.TINO_OIDC_CLIENT_ID)

_NOAUTH_USER = User(
    username='tino',
    email='tino@localhost',
    groups=list(config.TINO_ADMIN_GROUPS),
)


def get_current_user(request: Request) -> User:
    '''Extract the authenticated user from the session or an API key Bearer token.'''
    if config.TINO_AUTH_DISABLED:
        logger.debug('Auth disabled, returning noauth user')
        return _NOAUTH_USER

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        key = _api_key_service.verify(token)
        if key is None:
            logger.warning('Invalid API key from %s', request.url.path)
            raise HTTPException(401, 'Invalid API key')
        logger.debug('API key auth: %s (%s)', key['id'], key.get('label', ''))
        return User(
            username=f'apikey:{key["id"]}',
            email='',
            groups=[],
            api_key_access=key.get('access', {}),
        )

    user_data = request.session.get('user')
    if not user_data:
        logger.debug('No session user for %s', request.url.path)
        raise HTTPException(401, 'Not authenticated')
    return User(**user_data)


# ── Authorization ──


def is_global_admin(user: User) -> bool:
    '''Check if the user belongs to any of the configured admin groups.'''
    return bool(config.TINO_ADMIN_GROUPS & set(user.groups))


def resolve_role(user: User, access: list[AccessEntry], slug: str | None = None) -> str | None:
    '''Return the highest role the user holds in a bucket, or ``None`` if no access.

    For API key users the role is looked up directly from ``user.api_key_access``
    using *slug*; the bucket ACL is ignored.
    '''
    if user.api_key_access is not None:
        return user.api_key_access.get(slug) if slug else None

    if is_global_admin(user):
        return 'committer'

    if not access:
        default = config.TINO_DEFAULT_ROLE
        return default if default != 'none' else None

    best = None
    for entry in access:
        if entry.group in user.groups:
            if best is None or ROLE_HIERARCHY.get(entry.role, 0) > ROLE_HIERARCHY.get(best, 0):
                best = entry.role
    return best


def check_access(user: User, access: list[AccessEntry], min_role: str,
                 slug: str | None = None) -> None:
    '''Raise 403 if the user lacks the minimum required role on a bucket.'''
    if is_global_admin(user):
        return

    role = resolve_role(user, access, slug)
    if role is None:
        raise HTTPException(403, 'You do not have access to this bucket')

    if ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY.get(min_role, 0):
        raise HTTPException(403, f'{min_role} role required')

# ── Local Groups ──


def get_local_groups(email: str) -> list[str]:
    '''Load groups for an email from the .groups.yml file in the data dir.'''
    if not email:
        return []

    local_path = config.TINO_DATA_DIR / '.groups.yml'
    if not local_path.is_file():
        logger.warning('Local groups enabled, but file %s not found', local_path)
        return []

    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            group_map = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        logger.error('Failed to read or parse local groups from %s: %s', local_path, e)
        return []

    if not isinstance(group_map, dict):
        logger.error('Invalid format: %s must contain a dictionary mapping', local_path)
        return []

    # Build the list of lookup keys
    lookup_keys = ['*', email]
    if '@' in email:
        domain = email.split('@')[1]
        lookup_keys.append(f'*@{domain}')

    user_groups = set()

    # Process all keys in a single loop
    for key in lookup_keys:
        mapped_val = group_map.get(key)

        if not mapped_val:
            continue

        if isinstance(mapped_val, list):
            user_groups.update(mapped_val)
        else:
            logger.error('Invalid mapping for "%s" in %s: must be a list', key, local_path)

    logger.info('Local groups for "%s": %s', email, list(user_groups))

    return list(user_groups)

# ── Routes ──


@router.get('/login', include_in_schema=False)
async def login_page():
    '''Serve the login page.'''
    return FileResponse(_LOGIN_HTML)


@router.get('/oidc/login', include_in_schema=False)
async def login(request: Request):
    '''Redirect the user to the OIDC provider for authentication.'''
    redirect_uri = f'{config.TINO_BASE_URL}/oidc/callback'
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get('/oidc/callback', include_in_schema=False)
async def callback(request: Request):
    '''Handle the OIDC callback, exchange code for tokens, and create a session.'''
    token = await oauth.oidc.authorize_access_token(request)

    # Start from the ID-token claims, then enrich from the UserInfo endpoint
    # when the provider exposes one (it is only RECOMMENDED by OIDC Discovery).
    # Merging both keeps working whether the groups claim lands in the ID token
    # (e.g. Keycloak mapper set to "add to ID token") or only at UserInfo
    # (e.g. strict providers like Authelia) — reading just one drops the other.
    userinfo = dict(token.get('userinfo') or {})
    if oauth.oidc.server_metadata.get('userinfo_endpoint'):
        try:
            userinfo.update(await oauth.oidc.userinfo(token=token))
        except Exception:  # pylint: disable=broad-exception-caught
            # A missing/failing UserInfo endpoint must not break login when the
            # ID token already carries the claims — degrade, don't 500.
            logger.warning('UserInfo fetch failed; using ID-token claims', exc_info=True)

    if not userinfo:
        raise HTTPException(400, 'No user info in token response')

    email = userinfo.get('email', '')

    if config.TINO_LOCAL_GROUPS:
        # Resolve groups locally when TINO_LOCAL_GROUPS is enabled.
        groups = get_local_groups(email)
        if groups:
            logger.info('Loaded %d local groups for %s', len(groups), email)
    else:
        # Resolve groups using OIDC claims
        groups_claim = config.TINO_OIDC_GROUPS_CLAIM
        groups = userinfo.get(groups_claim, [])

    username = (
        userinfo.get('preferred_username')
        or userinfo.get('name')
        or userinfo.get('sub')
        or ''
    )

    request.session['user'] = {
        'username': username,
        'email': email,
        'groups': groups,
    }

    if token.get('id_token'):
        request.session['id_token'] = token['id_token']

    logger.info('Authenticated via OIDC (user: %s)', request.session['user']['username'])
    return RedirectResponse(url='/')


@router.get('/logout', include_in_schema=False)
async def logout(request: Request):
    '''Clear the session and redirect to the OIDC provider's logout endpoint.'''
    id_token = request.session.get('id_token')
    request.session.clear()
    login_url = f'{config.TINO_BASE_URL}/login'

    end_session_url = None
    try:
        metadata = await oauth.oidc.load_server_metadata()
        end_session_url = metadata.get('end_session_endpoint')
    except (OSError, KeyError, ValueError):
        logger.warning('Could not load OIDC metadata for logout')

    if end_session_url:
        params = f'post_logout_redirect_uri={login_url}'
        if id_token:
            params += f'&id_token_hint={id_token}'
        return RedirectResponse(url=f'{end_session_url}?{params}')

    return RedirectResponse(url='/login')


@router.get('/api/me')
async def me(user: User = Depends(get_current_user)):
    '''Return the currently authenticated user's info including admin status.'''
    data = user.model_dump()
    data['is_admin'] = is_global_admin(user)
    return data
