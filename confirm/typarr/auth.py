'''OIDC authentication and role-based access control.'''

from logging import getLogger
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from . import config
from .models import AccessEntry, User

logger = getLogger(__name__)

_LOGIN_HTML = str(Path(__file__).resolve().parent / 'static' / 'login.html')

router = APIRouter(tags=['auth'])

oauth = OAuth()

ROLE_HIERARCHY = {'viewer': 0, 'editor': 1, 'committer': 2}


# ── Authentication ──


async def setup_oauth():
    '''Register the OIDC provider with authlib and pre-fetch discovery metadata.'''
    oauth.register(
        name='oidc',
        client_id=config.OIDC_CLIENT_ID,
        client_secret=config.OIDC_CLIENT_SECRET,
        server_metadata_url=config.OIDC_DISCOVERY_URL,
        client_kwargs={'scope': 'openid email profile'},
    )
    await oauth.oidc.load_server_metadata()


def get_current_user(request: Request) -> User:
    '''Extract the authenticated user from the session.'''
    user_data = request.session.get('user')
    if not user_data:
        raise HTTPException(401, 'Not authenticated')
    return User(**user_data)


# ── Authorization ──


def is_global_admin(user: User) -> bool:
    '''Check if the user belongs to any of the configured admin groups.'''
    return bool(config.ADMIN_GROUPS & set(user.groups))


def resolve_role(user: User, access: list[AccessEntry]) -> str | None:
    '''Return the highest role the user holds in a bucket, or None if no access.'''
    if is_global_admin(user):
        return 'committer'
    if not access:
        default = config.DEFAULT_ROLE
        return default if default != 'none' else None
    best = None
    for entry in access:
        if entry.group in user.groups:
            if best is None or ROLE_HIERARCHY.get(entry.role, 0) > ROLE_HIERARCHY.get(best, 0):
                best = entry.role
    return best


def check_access(user: User, access: list[AccessEntry], min_role: str) -> None:
    '''Raise 403 if the user lacks the minimum required role on a bucket.'''
    if is_global_admin(user):
        return

    role = resolve_role(user, access)
    if role is None:
        raise HTTPException(403, 'You do not have access to this bucket')

    if ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY.get(min_role, 0):
        raise HTTPException(403, f'{min_role} role required')


# ── Routes ──


@router.get('/login')
async def login_page():
    '''Serve the login page.'''
    return FileResponse(_LOGIN_HTML)


@router.get('/oidc/login')
async def login(request: Request):
    '''Redirect the user to the OIDC provider for authentication.'''
    redirect_uri = str(request.url_for('callback'))
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get('/oidc/callback')
async def callback(request: Request):
    '''Handle the OIDC callback, exchange code for tokens, and create a session.'''
    token    = await oauth.oidc.authorize_access_token(request)
    userinfo = token.get('userinfo', {})

    if not userinfo:
        raise HTTPException(400, 'No user info in token response')

    groups_claim = config.OIDC_GROUPS_CLAIM

    request.session['user'] = {
        'username': userinfo.get('preferred_username', userinfo.get('sub', '')),
        'email': userinfo.get('email', ''),
        'groups': userinfo.get(groups_claim, []),
    }

    if token.get('id_token'):
        request.session['id_token'] = token['id_token']

    logger.info('User %s authenticated via OIDC', request.session['user']['username'])
    return RedirectResponse(url='/')


@router.get('/logout')
async def logout(request: Request):
    '''Clear the session and redirect to the OIDC provider's logout endpoint.'''
    id_token = request.session.get('id_token')
    request.session.clear()
    login_url = f'{request.base_url}login'

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


@router.get('/api/theme.css')
async def theme_css():
    '''Return CSS custom properties for the configured accent colour family.'''
    colour = config.ACCENT_COLOUR
    css = (
        ':root{'
        f'--accent-50:var(--cd-{colour}-50);'
        f'--accent-60:var(--cd-{colour}-60);'
        f'--accent-70:var(--cd-{colour}-70)'
        '}\n'
    )
    return Response(content=css, media_type='text/css')
