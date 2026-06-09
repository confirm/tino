.. _Development setup:

🛠️ Development setup
---------------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.14+
- Node.js (for vendored JS and linters)
- `Typst CLI <https://github.com/typst/typst>`_
- Git with `Git LFS <https://git-lfs.com/>`_

Project setup
~~~~~~~~~~~~~

Clone the repository and create a virtual environment:

.. code-block:: bash

    git clone https://github.com/confirm/tino.git
    cd tino
    make venv
    source .venv/bin/activate
    make develop

``make develop`` installs the Python package in editable mode (with dev dependencies) and the Node.js dependencies.

Running the dev server
~~~~~~~~~~~~~~~~~~~~~~

Start the development server with auto-reload:

.. code-block:: bash

    make server

This launches Uvicorn on ``http://localhost:8000`` with hot-reload enabled.
For convenience, ``make server`` sets dev-friendly defaults so it runs without any further configuration:

- ``TINO_AUTH_DISABLED=true``
- ``TINO_BASE_URL=http://localhost:8000``
- ``TINO_SECRET_KEY=develop`` (which keeps you logged in across reloads)

These defaults are overridable from your shell or the command line — for example, to run with authentication enabled (see :ref:`Deployment`):

.. code-block:: bash

    make server \
        TINO_AUTH_DISABLED=false \
        TINO_OIDC_DISCOVERY_URL=https://<sso-host>/realms/<realm>/.well-known/openid-configuration \
        TINO_OIDC_CLIENT_ID=tino \
        TINO_OIDC_CLIENT_SECRET=<secret>

Developing the MCP server
~~~~~~~~~~~~~~~~~~~~~~~~~

MCP OAuth requires a public HTTPS URL.
``localhost`` is not enough because the MCP client needs to reach TINO's well-known endpoints and the OIDC provider needs to redirect back to a real origin.

The easiest way to get one during development is a `Cloudflare Tunnel <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>`_ (``cloudflared``):

.. code-block:: bash

    # In one terminal — start TINO with auth enabled:
    TINO_AUTH_DISABLED=false \
    TINO_BASE_URL=https://<tunnel-host> \
    TINO_MCP_ENABLED=true \
    TINO_OIDC_DISCOVERY_URL=https://<sso-host>/realms/<realm>/.well-known/openid-configuration \
    TINO_OIDC_CLIENT_ID=tino \
    TINO_OIDC_CLIENT_SECRET=<secret> \
    make server

    # In another terminal — expose localhost via the tunnel:
    cloudflared tunnel --url http://localhost:8000

.. note::

    ``cloudflared`` prints the temporary public URL (e.g. ``https://random-words.trycloudflare.com``).
    Use that as ``TINO_BASE_URL``.

.. important::

   The tunnel hostname must be registered as a valid redirect URI in your OIDC provider (e.g. as a ``Valid redirect URIs`` entry in Keycloak).
   For a persistent hostname, create a `named tunnel <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/>`_ instead of the quick ``--url`` shortcut.

Once the tunnel is up, point an MCP client at it:

.. code-block:: console

    $ claude mcp add --transport http tino https://<tunnel-host>/mcp

Vendored assets
~~~~~~~~~~~~~~~

The CodeMirror editor is bundled into ``tino/static/js/vendor/codemirror.js``.
After modifying ``tino/static/js/codemirror-entry.js`` or updating Node dependencies, rebuild with:

.. code-block:: bash

    make vendor-js

The colours CSS is fetched separately:

.. code-block:: bash

    make vendor-css

Linting
~~~~~~~

Run all linters at once:

.. code-block:: bash

    make test

Or run them individually:

.. code-block:: bash

    make test-pycodestyle   # PEP 8
    make test-pylint        # Pylint
    make test-isort         # import order
    make test-eslint        # JavaScript
    make test-stylelint     # CSS

Building the docs
~~~~~~~~~~~~~~~~~

Build the documentation once:

.. code-block:: bash

    make docs

Or start a live-reloading preview:

.. code-block:: bash

    make autodocs

This opens the docs in your browser on ``http://localhost:8888`` and watches for changes.

Building the Docker image
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    make package            # creates a wheel in ``build/``
    make docker-image       # copies wheel from ``build/`` into Docker image.

Project layout
~~~~~~~~~~~~~~

::

    tino/
    ├── app.py              FastAPI application factory
    ├── auth.py             Authentication & OIDC
    ├── collab.py           Real-time collaboration (Yjs/WebSocket)
    ├── config.py           Environment-based configuration
    ├── dependencies.py     FastAPI dependency injection
    ├── mcp/                MCP server, OAuth resource server & instructions
    ├── middleware.py        ASGI middleware stack
    ├── models.py           Pydantic request/response schemas
    ├── notifier.py         File-change notifications
    ├── routers/            API endpoint modules
    ├── services/           Business logic (bucket, file, git, compiler, …)
    └── static/             SPA frontend
        ├── css/
        ├── js/             ES modules (no framework, vanilla JS)
        └── index.html
