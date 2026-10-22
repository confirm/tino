.. _Upgrade:

⬆️ Upgrade
==========

This page lists the **actions required** when upgrading TINO between versions —
configuration changes, renamed variables, and anything that needs attention before or after pulling a new image.

It is not a full changelog; only changes that ask something of you are recorded here.

.. important::

  Review this page before upgrading.
  Some releases add **required** settings that TINO refuses to start without, so an upgrade can otherwise fail at boot.

1.21.0
------

New MCP tools require reconnecting clients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :ref:`MCP server <MCP server>` gained new tools and options:

- ``edit_file`` changes parts of a file by exact string replacement, instead of rewriting the whole file.
- ``write_binary_file`` writes small binary files (e.g. images) from base64.
- ``read_file`` accepts ``offset`` and ``limit`` to read large files in ranges.

MCP clients fetch the tool list and the server instructions when they connect, and TINO does not notify connected clients about changes.
**Reconnect your MCP clients** after upgrading (e.g. restart the client or reconnect the server in its MCP settings), otherwise agents keep using the old tools only.

Compile errors are returned as structured diagnostics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a compilation fails, the compile endpoints (``GET /api/buckets/{slug}/compile/svg/…`` and ``…/compile/pdf/…``) still respond with ``422``, but the ``detail`` is now an **object** instead of a string:

.. code-block:: json

    {
      "detail": {
        "message": "error: unknown variable: foo\n  ┌─ main.typ:3:2\n…",
        "diagnostics": [
          {"severity": "error", "message": "unknown variable: foo", "file": "main.typ", "line": 3, "column": 2}
        ]
      }
    }

- ``message`` holds the compiler output; absolute server paths are stripped, so file paths are relative to the bucket.
- ``diagnostics`` lists every error and warning. ``file``, ``line`` and ``column`` are ``null`` when Typst reports no position.

The bundled web UI already handles the new format.
If you call the compile endpoints from scripts or integrations (e.g. with an :ref:`API key <usage/authentication:API keys>`) and read ``detail`` as a string, use ``detail.message`` instead.

1.20.0
------

MCP ``commit`` disabled by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :ref:`MCP server <MCP server>` no longer exposes the ``commit`` tool unless you opt in via the new :attr:`TINO_MCP_COMMIT_ENABLED <tino.config.TINO_MCP_COMMIT_ENABLED>` variable.

- By default agents can edit and compile files but **cannot commit** — humans review and commit via the UI.
- If you relied on agents committing over MCP, set ``TINO_MCP_COMMIT_ENABLED=true`` to restore the previous behaviour.

1.13.0
------

``TINO_BASE_URL`` is now required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TINO no longer derives its public address from the incoming request and reverse-proxy headers:

- You must set :attr:`TINO_BASE_URL <tino.config.TINO_BASE_URL>` to the externally reachable URL of your instance.
- ``TINO_TRUSTED_PROXIES`` has been **removed**, so you can drop it from your configuration.

.. note:: 

  Previously the OIDC redirect URL was built from the request and the ``X-Forwarded-Proto`` / ``X-Forwarded-Host`` headers. 
  A misconfigured proxy could silently produce a wrong ``http://`` redirect that the provider then rejected.
  Setting the URL explicitly removes that ambiguity — at the cost of making the variable mandatory.

1.12.0
------

Typarr becomes TINO
~~~~~~~~~~~~~~~~~~~~

The project has been renamed from **Typarr** to **TINO** (see :ref:`Name`).
This affects:

- The Docker image
- All environment variables
- The OIDC client
- The system user inside the container

Docker image
^^^^^^^^^^^^

Switch to the new Docker image:

.. code-block:: diff

   - image: ghcr.io/confirm/typarr
   + image: ghcr.io/confirm/tino

Environment variables
^^^^^^^^^^^^^^^^^^^^^

Every ``TYPARR_`` variable has been renamed to ``TINO_``.
Update your ``docker-compose.yml``, ``.env`` file, or orchestrator configuration accordingly.

OIDC client
^^^^^^^^^^^

The default ``TINO_OIDC_CLIENT_ID`` changed from ``typarr`` to ``tino``.
If your identity provider is configured with the old client ID ``typarr``, either update the provider or set ``TINO_OIDC_CLIENT_ID=typarr`` explicitly.

Container user
^^^^^^^^^^^^^^

The system user and group inside the container changed from ``typarr`` (UID/GID 1234) to ``tino`` (same UID/GID 1234).
No action is needed for the data volume — the UID/GID are unchanged, so file permissions remain valid.
