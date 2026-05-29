'''
Typarr allows configuration via environment variables.

.. note::

    - Settings marked with 🔴 are explicitly required.
    - Settings marked with ⭕ are implicitly required, but have an overridable default.
'''

__all__ = (
    'TYPARR_ACCENT_COLOUR',
    'TYPARR_ADMIN_GROUPS',
    'TYPARR_AUTH_DISABLED',
    'TYPARR_BUCKET_DIR',
    'TYPARR_DATA_DIR',
    'TYPARR_DEFAULT_ROLE',
    'TYPARR_FONT_DIR',
    'TYPARR_LOG_LEVEL',
    'TYPARR_OIDC_CLIENT_ID',
    'TYPARR_OIDC_CLIENT_SECRET',
    'TYPARR_OIDC_DISCOVERY_URL',
    'TYPARR_OIDC_GROUPS_CLAIM',
    'TYPARR_PACKAGE_DIR',
    'TYPARR_SECRET_KEY',
    'TYPARR_TRUSTED_PROXIES',
)

import os
from logging import getLogger
from os import environ
from pathlib import Path
from secrets import token_hex
from sys import exit as sys_exit

#
# Application settings.
#
# Application level settings.
#

#: When set to ``true``, authentication is completely disabled.
#: All requests are treated as an admin user without requiring OIDC.
#: Intended for local development and demo environments only.
TYPARR_AUTH_DISABLED = environ.get('TYPARR_AUTH_DISABLED', '').lower() in {'1', 'true', 'yes'}

#: ⭕ The log level (must match one of the
#: `Python logging levels <https://docs.python.org/3/library/logging.html#logging-levels>`_).
TYPARR_LOG_LEVEL = environ.get('TYPARR_LOG_LEVEL', 'INFO')

#: ⭕ The CI accent colour family used across the UI.
#:
#: .. hint::
#:  Must match a family from the `confirm design colours <https://assets.confirm.ch/#colours>`_.
TYPARR_ACCENT_COLOUR = environ.get('TYPARR_ACCENT_COLOUR', 'orange')

_DEFAULT_DATA_DIR = str(Path(__file__).resolve().parent.parent / 'data')
#: ⭕ The root directory where all the user data is stored.
#:
#: .. important::
#:
#:  To persist the Typarr data, either use a
#:  `volume <https://docs.docker.com/engine/storage/volumes/>`_ or a
#:  `bind mount <https://docs.docker.com/engine/storage/bind-mounts/>`_ mounted on the path.
TYPARR_DATA_DIR = Path(environ.get('TYPARR_DATA_DIR', _DEFAULT_DATA_DIR))

_DEFAULT_BUCKET_DIR = str(TYPARR_DATA_DIR / 'buckets')
#: ⭕ The directory where bucket git repos are stored.
#:
#: .. hint::
#:  By default this is a sub directory of the :attr:`TYPARR_DATA_DIR`.
#:  In case you change it to be outside of the :attr:`TYPARR_DATA_DIR`, make sure you've a
#:  `volume`_ or a `bind mount`_ mounted on the path.
TYPARR_BUCKET_DIR = Path(environ.get('TYPARR_BUCKET_DIR', _DEFAULT_BUCKET_DIR))

_DEFAULT_PACKAGE_DIR = str(TYPARR_BUCKET_DIR / 'packages')
#: Optional directory for local Typst packages (``@local/name:version``).
#:
#: .. note::
#:  The package dir is passed as ``--package-path`` to the ``typst`` CLI.
#:
#: .. hint::
#:  When this directory is set to a sub-directory of the :attr:`TYPARR_BUCKET_DIR`,
#:  the package directory can act like a bucket, and it can be edited in the
#:  Typarr web UI directly.
#:
#:  If not set the a sub-directory of the :attr:`TYPARR_BUCKET_DIR`, packages must be
#:  provided to the Docker container via one of the following Docker options:
#:
#:  - Via a dedicated `volume`_ (at runtime)
#:  - Via a dedicated `bind mount`_ (at runtime)
#:  - Via `COPY <https://docs.docker.com/reference/dockerfile/#copy>`_ or
#:    `ADD <https://docs.docker.com/reference/dockerfile/#add>`_ during build time
TYPARR_PACKAGE_DIR = Path(environ.get('TYPARR_PACKAGE_DIR', _DEFAULT_PACKAGE_DIR))

_DEFAULT_FONT_DIR = str(TYPARR_DATA_DIR / 'fonts')
#: Optional directory for custom fonts.
#:
#: .. note::
#:  The font dir is passed as ``--font-path`` to the ``typst`` CLI.
#:
#: .. hint::
#:  By default this is a sub directory of the :attr:`TYPARR_DATA_DIR`.
#:  In case you change it to be outside of the :attr:`TYPARR_DATA_DIR`, make sure you've a
#:  `volume`_ or a `bind mount`_ mounted on the path.
TYPARR_FONT_DIR = Path(environ.get('TYPARR_FONT_DIR', _DEFAULT_FONT_DIR))

_TRUSTED_PROXIES = environ.get('TYPARR_TRUSTED_PROXIES', '')
#: Comma-separated list of trusted proxy IP addresses (e.g. ``127.0.0.1,10.0.0.0/8``).
#: When set, ``X-Forwarded-For`` and ``X-Forwarded-Proto`` headers from these
#: proxies are respected. Use ``*`` to trust all sources.
#: Leave empty when Typarr is not behind a reverse proxy.
TYPARR_TRUSTED_PROXIES: list[str] = [h.strip() for h in _TRUSTED_PROXIES.split(',') if h.strip()]

#: ⭕ Secret key for signing session cookies.
#:
#: .. hint::
#:  If not set explicitly, a random token is generated on every startup.
#:  This is secure, but it will invalidate all existing sessions and forces users to log in again
#:  after a container restart.
TYPARR_SECRET_KEY = environ.get('TYPARR_SECRET_KEY', token_hex(32))

_ADMIN_GROUPS_RAW = environ.get('TYPARR_ADMIN_GROUPS', 'admins')
#: ⭕ Comma-separated list of OIDC groups whose members are Typarr administrators.
TYPARR_ADMIN_GROUPS: set[str] = {g.strip() for g in _ADMIN_GROUPS_RAW.split(',') if g.strip()}

#: ⭕ The default role for authenticated users on buckets without an access list.
#: Must be one of ``viewer``, ``editor``, ``committer``, or ``none``.
#: When set to ``none``, only global admins can access buckets without an ACL.
TYPARR_DEFAULT_ROLE = environ.get('TYPARR_DEFAULT_ROLE', 'none')

#
# OIDC.
#
# Typarr requires users to login via OIDC logins.
#

#: 🔴 The OIDC discovery URL (e.g. ``https://sso.example.com/.well-known/openid-configuration``).
TYPARR_OIDC_DISCOVERY_URL = environ.get('TYPARR_OIDC_DISCOVERY_URL')

#: ⭕ The OIDC client ID.
TYPARR_OIDC_CLIENT_ID = environ.get('TYPARR_OIDC_CLIENT_ID', 'typarr')

#: 🔴 The OIDC client secret.
TYPARR_OIDC_CLIENT_SECRET = environ.get('TYPARR_OIDC_CLIENT_SECRET')

#: ⭕ The OIDC token claim that contains the user's group memberships.
TYPARR_OIDC_GROUPS_CLAIM = environ.get('TYPARR_OIDC_GROUPS_CLAIM', 'groups')


#
# Sanity checks.
#


def sanity_checks():  # pylint: disable=too-complex,too-many-branches
    '''Validate all required settings on startup. Exits with code 1 if any are missing.'''
    if TYPARR_AUTH_DISABLED:
        getLogger(__name__).warning(
            'Authentication is disabled — ensure Typarr is protected'
            ' by a reverse proxy or is not publicly accessible',
        )

    errors = {}

    if not TYPARR_DATA_DIR.is_dir():
        errors['TYPARR_DATA_DIR'] = f'{TYPARR_DATA_DIR} does not exist or is not a directory'
    elif not os.access(TYPARR_DATA_DIR, os.W_OK):
        errors['TYPARR_DATA_DIR'] = f'{TYPARR_DATA_DIR} is not writable'

    if not TYPARR_ADMIN_GROUPS:
        errors['TYPARR_ADMIN_GROUPS'] = 'Set to a comma-separated list of admin groups'

    if not TYPARR_AUTH_DISABLED:
        if not TYPARR_OIDC_DISCOVERY_URL:
            errors['TYPARR_OIDC_DISCOVERY_URL'] = 'Set to the OIDC discovery URL'

        if not TYPARR_OIDC_CLIENT_ID:
            errors['TYPARR_OIDC_CLIENT_ID'] = 'Set to the OIDC client ID'

        if not TYPARR_OIDC_CLIENT_SECRET:
            errors['TYPARR_OIDC_CLIENT_SECRET'] = 'Set to the OIDC client secret'

        if not TYPARR_OIDC_GROUPS_CLAIM:
            errors['TYPARR_OIDC_GROUPS_CLAIM'] = 'Set to the OIDC group claim'

    _valid_roles = {'viewer', 'editor', 'committer', 'none'}
    if TYPARR_DEFAULT_ROLE not in _valid_roles:
        errors['TYPARR_DEFAULT_ROLE'] = f'Must be one of: {", ".join(sorted(_valid_roles))}'

    # Must match colours of https://assets.confirm.ch/#colours.
    _valid_accents = {
        'grey', 'cold-grey', 'warm-grey',
        'red', 'orange', 'yellow',
        'olive', 'lime', 'green', 'sea-green',
        'blue', 'azure',
        'violet', 'purple', 'fuchsia', 'rose',
    }
    if TYPARR_ACCENT_COLOUR not in _valid_accents:
        errors['TYPARR_ACCENT_COLOUR'] = f'Must be one of: {", ".join(sorted(_valid_accents))}'

    if errors:
        for var, error in errors.items():
            getLogger(__name__).critical('ERROR: Missing variable %r → %s', var, error)
        sys_exit(1)
