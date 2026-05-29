.. _Deployment:

🚀 Deployment
=============

Typarr ships as a single Docker image with no external dependencies — just point it at an OIDC provider and add a data volume, and you're up.

.. _Quick start:

⚡ Quick start (demo)
---------------------

To try Typarr without setting up an OIDC provider, disable authentication:

.. code-block:: bash

    docker run -d \
        --name typarr \
        -e TYPARR_AUTH_DISABLED=true \
        -p 5000:5000 \
        -v data:/data \
        ghcr.io/confirm/typarr

.. seealso::

    See `Disabling authentication`_ for more information.

.. _Docker:

🐳 Docker
---------

Docker image
~~~~~~~~~~~~

To deploy Typarr, use the following Docker image:

.. code-block:: text

    ghcr.io/confirm/typarr

Docker command
~~~~~~~~~~~~~~

To deploy Typarr via a simple ``docker`` command, use the following CLI arguments:

.. code-block:: bash

    docker run -d \
        --name typarr \
        --read-only \
        --tmpfs /tmp \
        -e TYPARR_OIDC_DISCOVERY_URL=https://sso.example.com/.well-known/openid-configuration \
        -e TYPARR_OIDC_CLIENT_SECRET=change-me \
        -e TYPARR_TRUSTED_PROXIES='*' \
        -p 5000:5000 \
        -v data:/data \
        ghcr.io/confirm/typarr

.. hint::

    It's recommended to deploy Typarr via `Docker Compose`_.

Docker Compose
~~~~~~~~~~~~~~

Use the following ``docker-compose.yml`` file to start Typarr:

.. literalinclude:: _extras/docker-compose.yml
    :language: yaml

Then bring the stack up with:

.. code-block:: bash

    docker compose up -d

.. _Authentication setup:

🔐 Authentication setup
-----------------------

OIDC
~~~~

Typarr requires an OpenID Connect (OIDC) provider for authentication.
Any provider that supports `OpenID Connect Discovery <https://openid.net/specs/openid-connect-discovery-1_0.html>`_ is supported (e.g. Keycloak, Authentik, Azure AD, Okta, Zitadel).

Register a new client (application) with your OIDC provider:

1. Set the **client ID** to :attr:`TYPARR_OIDC_CLIENT_ID <typarr.config.TYPARR_OIDC_CLIENT_ID>`, or vice-versa
2. Set the **redirect URI** (callback URL) to:

   .. code-block:: text

       https://typarr.example.com/oidc/callback

3. Set the **post-logout redirect URI** to:

   .. code-block:: text

       https://typarr.example.com/login

4. Ensure the following **scopes** are enabled: ``openid``, ``email``, ``profile``.
5. Make sure the **ID token** includes a claim with the user's group memberships
   (see :attr:`TYPARR_OIDC_GROUPS_CLAIM <typarr.config.TYPARR_OIDC_GROUPS_CLAIM>`).
6. Make sure a user matches an admin group (see :attr:`TYPARR_ADMIN_GROUPS <typarr.config.TYPARR_ADMIN_GROUPS>`)
7. Set the :attr:`TYPARR_OIDC_CLIENT_SECRET <typarr.config.TYPARR_OIDC_CLIENT_SECRET>` to the **client secret**

.. hint::

    See :ref:`Configuration` for the full list of environment variables.

Disabling authentication
~~~~~~~~~~~~~~~~~~~~~~~~

For local development, demo environments or external authentication, 
you can disable the built-in OIDC authentication entirely by setting the 
:attr:`TYPARR_AUTH_DISABLED <typarr.config.TYPARR_AUTH_DISABLED>` environment variable:

.. code-block:: bash

    TYPARR_AUTH_DISABLED=true

.. warning::

    When authentication is disabled, all requests are treated as a built-in **no-auth** user
    with full administrator privileges. OIDC configuration is not required in this mode.

    In production this is only safe when Typarr sits behind a reverse proxy or gateway
    that already handles authentication (e.g. OAuth2 Proxy, Authelia, or a cloud IAP).

Reverse proxy
~~~~~~~~~~~~~

When Typarr runs behind a reverse proxy (e.g. nginx, Traefik, Caddy), set
:attr:`TYPARR_TRUSTED_PROXIES <typarr.config.TYPARR_TRUSTED_PROXIES>` so that
``X-Forwarded-For`` and ``X-Forwarded-Proto`` headers are respected.
This ensures OIDC redirect URIs are built with ``https://``.

.. code-block:: bash

    TYPARR_TRUSTED_PROXIES=*

Set it to ``*`` to trust all sources, or to a comma-separated list of proxy
IP addresses (e.g. ``127.0.0.1,10.0.0.0/8``) for stricter control.

.. hint::

    When ``TYPARR_TRUSTED_PROXIES`` is not set, forwarded headers are ignored.
