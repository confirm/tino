'''
TINO allows configuration via environment variables.

.. note::

    - Settings marked with 🔴 are explicitly required.
    - Settings marked with ⭕ are implicitly required, but have an overridable default.
'''

__all__ = (
    'TINO_ACCENT_COLOUR',
    'TINO_ADMIN_GROUPS',
    'TINO_AUTH_DISABLED',
    'TINO_BASE_URL',
    'TINO_BUCKET_DIR',
    'TINO_DATA_DIR',
    'TINO_DEFAULT_ROLE',
    'TINO_FONT_DIR',
    'TINO_LOG_LEVEL',
    'TINO_MCP_ENABLED',
    'TINO_MCP_INSTRUCTIONS',
    'TINO_OIDC_CLIENT_ID',
    'TINO_OIDC_CLIENT_SECRET',
    'TINO_OIDC_DISCOVERY_URL',
    'TINO_OIDC_GROUPS_CLAIM',
    'TINO_PACKAGE_DIR',
    'TINO_ROOM_TTL',
    'TINO_SAVE_DEBOUNCE_MS',
    'TINO_SECRET_KEY',
)

import os
from logging import getLogger
from os import environ
from pathlib import Path
from secrets import token_hex
from sys import exit as sys_exit

_TRUEISH = {'1', 'true', 'yes'}


# ----- 📂 Directories -----

_DEFAULT_DATA_DIR = str(Path(__file__).resolve().parent.parent / 'data')
#: ⭕ The root directory where all the user data is stored.
#:
#: .. important::
#:
#:  To persist the TINO data, either use a
#:  `volume <https://docs.docker.com/engine/storage/volumes/>`_ or a
#:  `bind mount <https://docs.docker.com/engine/storage/bind-mounts/>`_ mounted on the path.
TINO_DATA_DIR = Path(environ.get('TINO_DATA_DIR', _DEFAULT_DATA_DIR))

_DEFAULT_BUCKET_DIR = str(TINO_DATA_DIR / 'buckets')
#: ⭕ The directory where bucket git repos are stored.
#:
#: .. hint::
#:  By default this is a sub directory of the :attr:`TINO_DATA_DIR`.
#:  In case you change it to be outside of the :attr:`TINO_DATA_DIR`, make sure you've a
#:  `volume`_ or a `bind mount`_ mounted on the path.
TINO_BUCKET_DIR = Path(environ.get('TINO_BUCKET_DIR', _DEFAULT_BUCKET_DIR))

_DEFAULT_PACKAGE_DIR = str(TINO_BUCKET_DIR / 'packages')
#: Optional directory for local Typst packages (``@local/name:version``).
#:
#: .. note::
#:  The package dir is passed as ``--package-path`` to the ``typst`` CLI.
#:
#: .. hint::
#:  When this directory is set to a sub-directory of the :attr:`TINO_BUCKET_DIR`,
#:  the package directory can act like a bucket, and it can be edited in the
#:  TINO web UI directly.
#:
#:  If not set the a sub-directory of the :attr:`TINO_BUCKET_DIR`, packages must be
#:  provided to the Docker container via one of the following Docker options:
#:
#:  - Via a dedicated `volume`_ (at runtime)
#:  - Via a dedicated `bind mount`_ (at runtime)
#:  - Via `COPY <https://docs.docker.com/reference/dockerfile/#copy>`_ or
#:    `ADD <https://docs.docker.com/reference/dockerfile/#add>`_ during build time
TINO_PACKAGE_DIR = Path(environ.get('TINO_PACKAGE_DIR', _DEFAULT_PACKAGE_DIR))

_DEFAULT_FONT_DIR = str(TINO_DATA_DIR / 'fonts')
#: Optional directory for custom fonts.
#:
#: .. note::
#:  The font dir is passed as ``--font-path`` to the ``typst`` CLI.
#:
#: .. hint::
#:  By default this is a sub directory of the :attr:`TINO_DATA_DIR`.
#:  In case you change it to be outside of the :attr:`TINO_DATA_DIR`, make sure you've a
#:  `volume`_ or a `bind mount`_ mounted on the path.
TINO_FONT_DIR = Path(environ.get('TINO_FONT_DIR', _DEFAULT_FONT_DIR))


# ----- 🔐 Security settings -----

#: 🔴 TINO's public base URL (e.g. ``https://tino.example.com``), without a trailing path.
#: The externally reachable address of this instance.
TINO_BASE_URL = (environ.get('TINO_BASE_URL') or '').rstrip('/') or None

#: ⭕ Secret key for signing session cookies.
#:
#: .. hint::
#:  If not set explicitly, a random token is generated on every startup.
#:  This is secure, but it will invalidate all existing sessions and forces users to log in again
#:  after a container restart.
TINO_SECRET_KEY = environ.get('TINO_SECRET_KEY', token_hex(32))

#: When set to ``true``, authentication is completely disabled.
#: All requests are treated as an admin user without requiring OIDC.
#: Intended for local development and demo environments only.
TINO_AUTH_DISABLED = environ.get('TINO_AUTH_DISABLED', '').lower() in _TRUEISH

#: ⭕ The default role for authenticated users on buckets without an access list.
#: Must be one of ``viewer``, ``editor``, ``committer``, or ``none``.
#: When set to ``none``, only global admins can access buckets without an ACL.
TINO_DEFAULT_ROLE = environ.get('TINO_DEFAULT_ROLE', 'none')

_ADMIN_GROUPS_RAW = environ.get('TINO_ADMIN_GROUPS', 'admins')
#: ⭕ Comma-separated list of OIDC groups whose members are TINO administrators.
TINO_ADMIN_GROUPS: set[str] = {g.strip() for g in _ADMIN_GROUPS_RAW.split(',') if g.strip()}


# ----- 🔑 OIDC settings -----

#: 🔴 The OIDC discovery URL (e.g. ``https://sso.example.com/.well-known/openid-configuration``).
TINO_OIDC_DISCOVERY_URL = environ.get('TINO_OIDC_DISCOVERY_URL')

#: ⭕ The OIDC client ID.
TINO_OIDC_CLIENT_ID = environ.get('TINO_OIDC_CLIENT_ID', 'tino')

#: 🔴 The OIDC client secret.
TINO_OIDC_CLIENT_SECRET = environ.get('TINO_OIDC_CLIENT_SECRET')

#: ⭕ The OIDC token claim that contains the user's group memberships.
TINO_OIDC_GROUPS_CLAIM = environ.get('TINO_OIDC_GROUPS_CLAIM', 'groups')


# ----- 🤖 MCP -----

#: When set to ``true``, the :ref:`MCP <MCP server>` server is mounted at ``/mcp``.
#:
#: .. warning::
#:  The MCP server is **experimental** and disabled by default.
TINO_MCP_ENABLED = environ.get('TINO_MCP_ENABLED', '').lower() in _TRUEISH

#: Optional additional instructions appended to the built-in MCP server instructions.
#: Use this to provide global context to AI agents connecting via MCP
#: (e.g. house style, terminology, or organisational policies).
TINO_MCP_INSTRUCTIONS = environ.get('TINO_MCP_INSTRUCTIONS') or None


# ----- ⚙️ Application settings -----

#: ⭕ The CI accent colour family used across the UI.
#:
#: .. hint::
#:  Must match a family from the `confirm design colours <https://assets.confirm.ch/#colours>`_.
TINO_ACCENT_COLOUR = environ.get('TINO_ACCENT_COLOUR', 'orange')

#: ⭕ Delay in milliseconds before auto-saving after the user stops typing.
#:
#: .. hint::
#:  Set to ``0`` to disable auto-save.
#:
#: .. important::
#:  The document is rendered from the (saved) file on disk, thus auto saving is recommended.
TINO_SAVE_DEBOUNCE_MS = int(environ.get('TINO_SAVE_DEBOUNCE_MS', '250'))

#: ⭕ Seconds to keep a collaboration room alive after the last client disconnects.
#: Allows reconnecting clients (e.g. page refresh) to reuse the room.
TINO_ROOM_TTL = int(environ.get('TINO_ROOM_TTL', '300'))

#: ⭕ The log level (must match one of the
#: `Python logging levels <https://docs.python.org/3/library/logging.html#logging-levels>`_).
TINO_LOG_LEVEL = environ.get('TINO_LOG_LEVEL', 'INFO')


# ----- Sanity checks -----

def sanity_checks():  # pylint: disable=too-complex,too-many-branches
    '''Validate all required settings on startup. Exits with code 1 if any are missing.'''
    if TINO_AUTH_DISABLED:
        getLogger(__name__).warning(
            'Authentication is disabled — ensure TINO is protected'
            ' by a reverse proxy or is not publicly accessible',
        )

    errors = {}

    if not TINO_DATA_DIR.is_dir():
        errors['TINO_DATA_DIR'] = f'{TINO_DATA_DIR} does not exist or is not a directory'
    elif not os.access(TINO_DATA_DIR, os.W_OK):
        errors['TINO_DATA_DIR'] = f'{TINO_DATA_DIR} is not writable'

    if not TINO_BASE_URL:
        errors['TINO_BASE_URL'] = "Set to TINO's public base URL"
    elif not TINO_BASE_URL.startswith(('https://', 'http://localhost', 'http://127.0.0.1')):
        errors['TINO_BASE_URL'] = (
            'Must start with https:// (or http://localhost / http://127.0.0.1 for development)'
        )

    if not TINO_ADMIN_GROUPS:
        errors['TINO_ADMIN_GROUPS'] = 'Set to a comma-separated list of admin groups'

    if not TINO_AUTH_DISABLED:
        if not TINO_OIDC_DISCOVERY_URL:
            errors['TINO_OIDC_DISCOVERY_URL'] = 'Set to the OIDC discovery URL'

        if not TINO_OIDC_CLIENT_ID:
            errors['TINO_OIDC_CLIENT_ID'] = 'Set to the OIDC client ID'

        if not TINO_OIDC_CLIENT_SECRET:
            errors['TINO_OIDC_CLIENT_SECRET'] = 'Set to the OIDC client secret'

        if not TINO_OIDC_GROUPS_CLAIM:
            errors['TINO_OIDC_GROUPS_CLAIM'] = 'Set to the OIDC group claim'

        if TINO_MCP_ENABLED and not TINO_BASE_URL:
            errors['TINO_BASE_URL'] = (
                "Set to TINO's public base URL (or disable MCP with TINO_MCP_ENABLED=false)"
            )

    _valid_roles = {'viewer', 'editor', 'committer', 'none'}
    if TINO_DEFAULT_ROLE not in _valid_roles:
        errors['TINO_DEFAULT_ROLE'] = f'Must be one of: {", ".join(sorted(_valid_roles))}'

    # Must match colours of https://assets.confirm.ch/#colours.
    _valid_accents = {
        'grey', 'cold-grey', 'warm-grey',
        'red', 'orange', 'yellow',
        'olive', 'lime', 'green', 'sea-green',
        'blue', 'azure',
        'violet', 'purple', 'fuchsia', 'rose',
    }
    if TINO_ACCENT_COLOUR not in _valid_accents:
        errors['TINO_ACCENT_COLOUR'] = f'Must be one of: {", ".join(sorted(_valid_accents))}'

    if errors:
        for var, error in errors.items():
            getLogger(__name__).critical('ERROR: Missing variable %r → %s', var, error)
        sys_exit(1)
