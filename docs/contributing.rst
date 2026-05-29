.. _Contributing:

🤝 Contributing
---------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.14+
- Node.js (for vendored JS and linters)
- `Typst CLI <https://github.com/typst/typst>`_
- Git

Project setup
~~~~~~~~~~~~~

Clone the repository and create a virtual environment:

.. code-block:: bash

    git clone https://github.com/confirm/typarr.git
    cd typarr
    make venv
    source .venv/bin/activate
    make develop

``make develop`` installs the Python package in editable mode (with dev
dependencies) and the Node.js dependencies.

Running the dev server
~~~~~~~~~~~~~~~~~~~~~~

Start the development server with auto-reload:

.. code-block:: bash

    make server

This launches Uvicorn on ``http://localhost:8000`` with hot-reload enabled.
To skip authentication during development, set:

.. code-block:: bash

    TYPARR_AUTH_DISABLED=true make server

Vendored assets
~~~~~~~~~~~~~~~

Some front-end libraries (Prism.js, Yjs) are bundled into the
``typarr/static/js/vendor/`` directory. After modifying
``typarr/static/js/yjs-entry.js`` or updating Node dependencies, rebuild
with:

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

This opens the docs in your browser on ``http://localhost:8888`` and
watches for changes.

Building the Docker image
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    make package
    make docker-image

``make package`` creates a wheel in ``build/``, which the Dockerfile
copies into the image.

Project layout
~~~~~~~~~~~~~~

::

    typarr/
    ├── auth.py             Authentication & OIDC
    ├── config.py           Environment-based configuration
    ├── dependencies.py     FastAPI dependency injection
    ├── middleware.py        ASGI middleware stack
    ├── models.py           Pydantic request/response schemas
    ├── routers/            API endpoint modules
    ├── services/           Business logic (bucket, file, git, compiler, …)
    └── static/             SPA frontend
        ├── css/
        ├── js/             ES modules (no framework, vanilla JS)
        └── index.html
