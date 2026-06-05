.. _Deployment:

🚀 Deployment
=============

TINO ships as a single Docker image with no external dependencies — just point it at an OIDC provider and add a data volume, and you're up.

.. _Quick start:

⚡ Quick start (demo)
---------------------

To try TINO without setting up an OIDC provider, disable authentication:

.. code-block:: bash

    docker run -d \
        --name tino \
        -e TINO_AUTH_DISABLED=true \
        -p 5000:5000 \
        -v data:/data \
        ghcr.io/confirm/tino

.. seealso::

    See `Disabling authentication`_ for more information.

.. _Docker:

🐳 Docker
---------

Docker image
~~~~~~~~~~~~

To deploy TINO, use the following Docker image:

.. code-block:: text

    ghcr.io/confirm/tino

.. seealso::

    Check the `Git tags <https://github.com/confirm/tino/tags>`_ for explicit Docker image versions.

Docker command
~~~~~~~~~~~~~~

To deploy TINO via a simple ``docker`` command, use the following CLI arguments:

.. code-block:: bash

    docker run -d \
        --name tino \
        --read-only \
        --tmpfs /tmp \
        -e TINO_BASE_URL=https://tino.example.com \
        -e TINO_OIDC_DISCOVERY_URL=https://sso.example.com/.well-known/openid-configuration \
        -e TINO_OIDC_CLIENT_SECRET=change-me \
        -p 5000:5000 \
        -v data:/data \
        ghcr.io/confirm/tino

.. hint::

    It's recommended to deploy TINO via `Docker Compose`_.

Docker Compose
~~~~~~~~~~~~~~

Use the following ``docker-compose.yml`` `Compose file </docker-compose.yml>`_ to start TINO:

.. literalinclude:: ../_extras/docker-compose.yml
    :language: yaml

Then bring the stack up with:

.. code-block:: bash

    docker compose up -d

.. _Standalone:

📦 Standalone (without Docker)
------------------------------

.. warning::

   Running TINO without Docker is **not recommended and unsupported**.
   You are responsible for managing Python, the Typst CLI, process
   supervision, and upgrades yourself.  The Docker image is the only
   officially supported deployment method.

If you cannot use Docker, TINO can be installed as a regular Python package
and run with Gunicorn.

Prerequisites
~~~~~~~~~~~~~

- Python 3.14+
- `Typst CLI <https://github.com/typst/typst>`_ available on ``$PATH``
- Git with `Git LFS <https://git-lfs.com/>`_

Building the wheel
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    make package

This produces a wheel in ``build/`` (e.g. ``build/tino-<version>-py3-none-any.whl``).

Installing
~~~~~~~~~~

.. code-block:: bash

    pip install build/tino-*.whl

This installs TINO and all its Python dependencies (including Gunicorn and
Uvicorn).

Running
~~~~~~~

.. code-block:: bash

    export TINO_BASE_URL=https://tino.example.com
    export TINO_OIDC_DISCOVERY_URL=https://sso.example.com/.well-known/openid-configuration
    export TINO_OIDC_CLIENT_SECRET=change-me
    # … set any other TINO_* variables (see Configuration)

    gunicorn \
        -k uvicorn.workers.UvicornWorker \
        -w 1 \
        -b 0.0.0.0:5000 \
        'tino:create_app()'

This is the same command the Docker image runs internally.

.. hint::

    See :ref:`Configuration` for the full list of environment variables.
    Make sure :attr:`TINO_DATA_DIR <tino.config.TINO_DATA_DIR>` points to a
    writable directory that is backed up regularly.

.. _Integration:

🔗 Integration
--------------

Reverse proxy
~~~~~~~~~~~~~

TINO is typically deployed behind a reverse proxy (e.g. nginx, Traefik, Caddy) that terminates TLS.

Set :attr:`TINO_BASE_URL <tino.config.TINO_BASE_URL>` to the public ``https://`` URL the proxy serves TINO on.
It is used to build OIDC redirect URLs and, when :ref:`MCP <MCP server>` is enabled, as the resource identifier in the OAuth discovery metadata.

OIDC
~~~~

TINO requires an **OAuth 2.0** / OpenID Connect (OIDC) provider for authentication.
Any provider that supports `OpenID Connect Discovery <https://openid.net/specs/openid-connect-discovery-1_0.html>`_ is supported (e.g. Keycloak, Authentik, Azure AD, Okta, Zitadel).

Register a new client (application) with your OIDC provider:

1. Set the **client ID** to :attr:`TINO_OIDC_CLIENT_ID <tino.config.TINO_OIDC_CLIENT_ID>`, or vice-versa
2. Set the **redirect URI** (callback URL) to:

   .. code-block:: text

       https://tino.example.com/oidc/callback

3. Set the **post-logout redirect URI** to:

   .. code-block:: text

       https://tino.example.com/login

4. Ensure the following **scopes** are enabled: ``openid``, ``email``, ``profile``.
5. Make sure the **ID token** includes a claim with the user's group memberships
   (see :attr:`TINO_OIDC_GROUPS_CLAIM <tino.config.TINO_OIDC_GROUPS_CLAIM>`).
6. Make sure a user matches an admin group (see :attr:`TINO_ADMIN_GROUPS <tino.config.TINO_ADMIN_GROUPS>`)
7. Set the :attr:`TINO_OIDC_CLIENT_SECRET <tino.config.TINO_OIDC_CLIENT_SECRET>` to the **client secret**

.. seealso::

    See :ref:`Configuration` for the full list of environment variables.

MCP
~~~

The :ref:`MCP server <MCP server>` is disabled by default.
To enable it, set :attr:`TINO_MCP_ENABLED <tino.config.TINO_MCP_ENABLED>` to ``true``.

MCP authentication happens via **OAuth 2.0**, and the OIDC provider must support CIMD.
No additional client registration is needed.

.. note::

    On `Keycloak <https://www.keycloak.org/>`_ this requires version `26.6.0 <https://www.keycloak.org/2026/04/keycloak-2660-released>`_ or later, where `Client ID Metadata Document <https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/>`_ support ships as an experimental feature.
    Check out the `Client Registration <https://www.keycloak.org/securing-apps/mcp-authz-server#_client_registration>`_ docs for more information.

.. seealso::

    Check out the :ref:`MCP authentication <MCP authentication>` for how the auth flow works, and the :ref:`MCP configuration <MCP configuration>` for the full list of MCP-related settings.

Disabling authentication
~~~~~~~~~~~~~~~~~~~~~~~~

For local development, demo environments or external authentication, you can disable the built-in OIDC authentication entirely by setting the :attr:`TINO_AUTH_DISABLED <tino.config.TINO_AUTH_DISABLED>` environment variable:

.. code-block:: bash

    TINO_AUTH_DISABLED=true

.. warning::

    When authentication is disabled, all requests are treated as a built-in **no-auth** user with full administrator privileges. 
    OIDC configuration is not required in this mode.

    In production this is only safe when TINO sits behind a reverse proxy or gateway that already handles authentication (e.g. OAuth2 Proxy, Authelia, or a cloud IAP).
