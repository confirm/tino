.. _Deployment:

🚀 Deployment
=============

Typr ships as a single Docker image with no external dependencies — just point it at an OIDC provider and add a data volume, and you're up.

.. _Docker:

🐳 Docker
---------

Docker image
~~~~~~~~~~~~

To deploy Typr, use the following Docker image:

.. code-block:: text

    harbor.confirm.ch/typr/typr

Docker command
~~~~~~~~~~~~~~

To deploy Typr via a simple ``docker`` command, use the following CLI arguments:

.. code-block:: bash

    docker run -d \
        --name typr \
        -e OIDC_DISCOVERY_URL=https://sso.example.com/.well-known/openid-configuration \
        -e OIDC_CLIENT_SECRET=change-me \
        -p 5000:5000 \
        -v data:/data \
        harbor.confirm.ch/typr/typr

.. hint:: 

    It's recommended to deploy Typr via `Docker Compose`_.

Docker Compose
~~~~~~~~~~~~~~

Use the following ``docker-compose.yml`` file to start Typr:

.. literalinclude:: _extras/docker-compose.yml
    :language: yaml

Then bring the stack up with:

.. code-block:: bash

    docker compose up -d

.. _OIDC:

🔐 OIDC
-------

Typr requires an OpenID Connect (OIDC) provider for authentication.
Any provider that supports `OpenID Connect Discovery <https://openid.net/specs/openid-connect-discovery-1_0.html>`_ is supported (e.g. Keycloak, Authentik, Azure AD, Okta, Zitadel).

Register a new client (application) with your OIDC provider:

1. Set the **client ID** to :attr:`OIDC_CLIENT_ID <confirm.typr.config.OIDC_CLIENT_ID>`, or vice-versa
2. Set the **redirect URI** (callback URL) to:

   .. code-block:: text

       https://typr.example.com/oidc/callback

3. Set the **post-logout redirect URI** to:

   .. code-block:: text

       https://typr.example.com/login

4. Ensure the following **scopes** are enabled: ``openid``, ``email``, ``profile``.
5. Make sure the **ID token** includes a claim with the user's group memberships
   (see :attr:`OIDC_GROUPS_CLAIM <confirm.typr.config.OIDC_GROUPS_CLAIM>`).
6. Make sure a user matches an admin group (see :attr:`ADMIN_GROUPS <confirm.typr.config.ADMIN_GROUPS>`)
7. Set the :attr:`OIDC_CLIENT_SECRET <confirm.typr.config.OIDC_CLIENT_SECRET>` to the **client secret**

.. hint::

    See :ref:`Configuration` for the full list of environment variables.

Reverse proxy
~~~~~~~~~~~~~

When Typr runs behind a reverse proxy (e.g. nginx, Traefik, Caddy), the proxy
must forward the original protocol and client address so that OIDC redirect URIs
are built with ``https://``. Ensure your proxy sets:

- ``X-Forwarded-Proto``
- ``X-Forwarded-For``

Typr reads and respects these headers automatically.

.. todo::

    Make this configurable in case no reverse-proxy is in front (security issue).
