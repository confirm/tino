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
        -e AUTH_DISABLED=true \
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
        -e OIDC_DISCOVERY_URL=https://sso.example.com/.well-known/openid-configuration \
        -e OIDC_CLIENT_SECRET=change-me \
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

🔐 Authentication
-----------------

OIDC
~~~~

Typarr requires an OpenID Connect (OIDC) provider for authentication.
Any provider that supports `OpenID Connect Discovery <https://openid.net/specs/openid-connect-discovery-1_0.html>`_ is supported (e.g. Keycloak, Authentik, Azure AD, Okta, Zitadel).

Register a new client (application) with your OIDC provider:

1. Set the **client ID** to :attr:`OIDC_CLIENT_ID <typarr.config.OIDC_CLIENT_ID>`, or vice-versa
2. Set the **redirect URI** (callback URL) to:

   .. code-block:: text

       https://typarr.example.com/oidc/callback

3. Set the **post-logout redirect URI** to:

   .. code-block:: text

       https://typarr.example.com/login

4. Ensure the following **scopes** are enabled: ``openid``, ``email``, ``profile``.
5. Make sure the **ID token** includes a claim with the user's group memberships
   (see :attr:`OIDC_GROUPS_CLAIM <typarr.config.OIDC_GROUPS_CLAIM>`).
6. Make sure a user matches an admin group (see :attr:`ADMIN_GROUPS <typarr.config.ADMIN_GROUPS>`)
7. Set the :attr:`OIDC_CLIENT_SECRET <typarr.config.OIDC_CLIENT_SECRET>` to the **client secret**

.. hint::

    See :ref:`Configuration` for the full list of environment variables.

Disabling authentication
~~~~~~~~~~~~~~~~~~~~~~~~

For local development, demo environments or external authentication, 
you can disable the built-in OIDC authentication entirely by setting the 
:attr:`AUTH_DISABLED <typarr.config.AUTH_DISABLED>` environment variable:

.. code-block:: bash

    AUTH_DISABLED=true

.. warning::

    When authentication is disabled, all requests are treated as a built-in **no-auth** user
    with full administrator privileges. OIDC configuration is not required in this mode.

    In production this is only safe when Typarr sits behind a reverse proxy or gateway
    that already handles authentication (e.g. OAuth2 Proxy, Authelia, or a cloud IAP).

Reverse proxy
~~~~~~~~~~~~~

When Typarr runs behind a reverse proxy (e.g. nginx, Traefik, Caddy), the proxy
must forward the original protocol and client address so that OIDC redirect URIs
are built with ``https://``. Ensure your proxy sets:

- ``X-Forwarded-Proto``
- ``X-Forwarded-For``

Typarr reads and respects these headers automatically.

.. todo::

    Make this configurable in case no reverse-proxy is in front (security issue).
