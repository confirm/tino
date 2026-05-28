'''
Typarr allows configuration via environment variables.

.. note::

    - Settings marked with 🔴 are explicitly required.
    - Settings marked with ⭕ are implicitly required, but have an overridable default.
'''

__all__ = (
    'ACCENT_COLOUR',
    'ADMIN_GROUPS',
    'BUCKET_DIR',
    'DATA_DIR',
    'DEFAULT_ROLE',
    'FONT_DIR',
    'LOG_LEVEL',
    'OIDC_CLIENT_ID',
    'OIDC_CLIENT_SECRET',
    'OIDC_DISCOVERY_URL',
    'OIDC_GROUPS_CLAIM',
    'PACKAGE_DIR',
    'SECRET_KEY',
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


#: ⭕ The log level (must match one of the
#: `Python logging levels <https://docs.python.org/3/library/logging.html#logging-levels>`_).
LOG_LEVEL = environ.get('LOG_LEVEL', 'INFO')

#: ⭕ The CI accent colour family used across the UI.
#:
#: .. hint::
#:  Must match a family from the `confirm design colours <https://assets.confirm.ch/#colours>`_.
ACCENT_COLOUR = environ.get('ACCENT_COLOUR', 'orange')

_DEFAULT_DATA_DIR = str(Path(__file__).resolve().parent.parent.parent / 'data')
#: ⭕ The root directory where all the user data is stored.
#:
#: .. important::
#:
#:  To persist the Typarr data, either use a
#:  `volume <https://docs.docker.com/engine/storage/volumes/>`_ or a
#:  `bind mount <https://docs.docker.com/engine/storage/bind-mounts/>`_ mounted on the path.
DATA_DIR = Path(environ.get('DATA_DIR', _DEFAULT_DATA_DIR))

_DEFAULT_BUCKET_DIR = str(DATA_DIR / 'buckets')
#: ⭕ The directory where bucket git repos are stored.
#:
#: .. hint::
#:  By default this is a sub directory of the :attr:`DATA_DIR`.
#:  In case you change it to be outside of the :attr:`DATA_DIR`, make sure you've a
#:  `volume`_ or a `bind mount`_ mounted on the path.
BUCKET_DIR = Path(environ.get('BUCKET_DIR', _DEFAULT_BUCKET_DIR))

_DEFAULT_PACKAGE_DIR = str(BUCKET_DIR / 'packages')
#: Optional directory for local Typst packages (``@local/name:version``).
#:
#: .. note::
#:  The package dir is passed as ``--package-path`` to the ``typst`` CLI.
#:
#: .. hint::
#:  When this directory is set to a sub-directory of the :attr:`BUCKET_DIR`,
#:  the package directory can act like a bucket, and it can be edited in the
#:  Typarr web UI directly.
#:
#:  If not set the a sub-directory of the :attr:`BUCKET_DIR`, packages must be
#:  provided to the Docker container via one of the following Docker options:
#:
#:  - Via a dedicated `volume`_ (at runtime)
#:  - Via a dedicated `bind mount`_ (at runtime)
#:  - Via `COPY <https://docs.docker.com/reference/dockerfile/#copy>`_ or `ADD <https://docs.docker.com/reference/dockerfile/#add>`_ during build time
PACKAGE_DIR = Path(environ.get('PACKAGE_DIR', _DEFAULT_PACKAGE_DIR))

_DEFAULT_FONT_DIR = str(DATA_DIR / 'fonts')
#: Optional directory for custom fonts.
#:
#: .. note::
#:  The font dir is passed as ``--font-path`` to the ``typst`` CLI.
#:
#: .. hint::
#:  By default this is a sub directory of the :attr:`DATA_DIR`.
#:  In case you change it to be outside of the :attr:`DATA_DIR`, make sure you've a
#:  `volume`_ or a `bind mount`_ mounted on the path.
FONT_DIR = Path(environ.get('FONT_DIR', _DEFAULT_FONT_DIR))

#: ⭕ Secret key for signing session cookies.
#:
#: .. hint::
#:  If not set explicitly, a random token is generated on every startup.
#:  This is secure, but it will invalidate all existing sessions and forces users to log in again
#:  after a container restart.
SECRET_KEY = environ.get('SECRET_KEY', token_hex(32))

_ADMIN_GROUPS_RAW = environ.get('ADMIN_GROUPS', 'admins')
#: ⭕ Comma-separated list of OIDC groups whose members are Typarr administrators.
ADMIN_GROUPS: set[str] = {g.strip() for g in _ADMIN_GROUPS_RAW.split(',') if g.strip()}

#: ⭕ The default role for authenticated users on buckets without an access list.
#: Must be one of ``viewer``, ``editor``, ``committer``, or ``none``.
#: When set to ``none``, only global admins can access buckets without an ACL.
DEFAULT_ROLE = environ.get('DEFAULT_ROLE', 'none')

#
# OIDC.
#
# Typarr requires users to login via OIDC logins.
#

#: 🔴 The OIDC discovery URL (e.g. ``https://sso.example.com/.well-known/openid-configuration``).
OIDC_DISCOVERY_URL = environ.get('OIDC_DISCOVERY_URL')

#: ⭕ The OIDC client ID.
OIDC_CLIENT_ID = environ.get('OIDC_CLIENT_ID', 'typarr')

#: 🔴 The OIDC client secret.
OIDC_CLIENT_SECRET = environ.get('OIDC_CLIENT_SECRET')

#: ⭕ The OIDC token claim that contains the user's group memberships.
OIDC_GROUPS_CLAIM = environ.get('OIDC_GROUPS_CLAIM', 'groups')


#
# Sanity checks.
#


def sanity_checks():  # pylint: disable=too-complex
    '''Validate all required settings on startup. Exits with code 1 if any are missing.'''
    errors = {}

    if not DATA_DIR.is_dir():
        errors['DATA_DIR'] = f'{DATA_DIR} does not exist or is not a directory'
    elif not os.access(DATA_DIR, os.W_OK):
        errors['DATA_DIR'] = f'{DATA_DIR} is not writable'

    if not ADMIN_GROUPS:
        errors['ADMIN_GROUPS'] = 'Set to a comma-separated list of admin groups'

    if not OIDC_DISCOVERY_URL:
        errors['OIDC_DISCOVERY_URL'] = 'Set to the OIDC discovery URL'

    if not OIDC_CLIENT_ID:
        errors['OIDC_CLIENT_ID'] = 'Set to the OIDC client ID'

    if not OIDC_CLIENT_SECRET:
        errors['OIDC_CLIENT_SECRET'] = 'Set to the OIDC client secret'

    if not OIDC_GROUPS_CLAIM:
        errors['OIDC_GROUPS_CLAIM'] = 'Set to the OIDC group claim'

    _valid_roles = {'viewer', 'editor', 'committer', 'none'}
    if DEFAULT_ROLE not in _valid_roles:
        errors['DEFAULT_ROLE'] = f'Must be one of: {", ".join(sorted(_valid_roles))}'

    # Must match colours of https://assets.confirm.ch/#colours.
    _valid_accents = {
        'grey', 'cold-grey', 'warm-grey',
        'red', 'orange', 'yellow',
        'olive', 'lime', 'green', 'sea-green',
        'blue', 'azure',
        'violet', 'purple', 'fuchsia', 'rose',
    }
    if ACCENT_COLOUR not in _valid_accents:
        errors['ACCENT_COLOUR'] = f'Must be one of: {", ".join(sorted(_valid_accents))}'

    if errors:
        for var, error in errors.items():
            getLogger(__name__).critical('ERROR: Missing variable %r → %s', var, error)
        sys_exit(1)
