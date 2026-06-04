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

Use the following ``docker-compose.yml`` file to start TINO:

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

TINO requires an OpenID Connect (OIDC) provider for authentication.
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

.. hint::

    See :ref:`Configuration` for the full list of environment variables.

Disabling authentication
~~~~~~~~~~~~~~~~~~~~~~~~

For local development, demo environments or external authentication, you can disable the built-in OIDC authentication entirely by setting the :attr:`TINO_AUTH_DISABLED <tino.config.TINO_AUTH_DISABLED>` environment variable:

.. code-block:: bash

    TINO_AUTH_DISABLED=true

.. warning::

    When authentication is disabled, all requests are treated as a built-in **no-auth** user with full administrator privileges. 
    OIDC configuration is not required in this mode.

    In production this is only safe when TINO sits behind a reverse proxy or gateway that already handles authentication (e.g. OAuth2 Proxy, Authelia, or a cloud IAP).

Reverse proxy
~~~~~~~~~~~~~

TINO is typically deployed behind a reverse proxy (e.g. nginx, Traefik, Caddy) that terminates TLS.
Set :attr:`TINO_BASE_URL <tino.config.TINO_BASE_URL>` to the public ``https://`` URL the proxy serves TINO on — it is used to build the OIDC redirect URLs.
