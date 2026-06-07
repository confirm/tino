.. _MCP server:

🤖 MCP server
-------------

.. warning::

   The MCP server is **experimental**.

   It depends on your OIDC provider acting as a :ref:`CIMD-capable authorisation server <usage/authentication:MCP>`,
   and the surrounding ecosystem is still stabilising.

   There are also 2 known issues ocurred during the development in combination with Keycloak:

   - `Keycloak missing "none" in token_endpoint_auth_methods_supported breaks MCP CIMD <https://github.com/confirm/tino/issues/23>`_
   - `Keycloak CIMD tokens omit aud, so MCP access tokens aren't audience-bound to TINO <https://github.com/confirm/tino/issues/24>`_

   It is disabled by default — enable it at your own risk.

.. seealso::

    Have a look at the :ref:`Vision` for where AI-driven document generation fits into TINO's direction, and :ref:`ADR-10` for the design rationale.

TINO ships with a built-in `Model Context Protocol <https://modelcontextprotocol.io/>`_ (MCP) server that exposes buckets, files, compilation, and git as **tools** for AI agents.
An assistant can list buckets, read and write Typst files, compile them to check for errors, and commit the result.
All through TINO, with the same access rules as a human user.

Connecting a client
~~~~~~~~~~~~~~~~~~~

1. Enable the MCP server (see :attr:`TINO_MCP_ENABLED <tino.config.TINO_MCP_ENABLED>`)
2. Point any MCP-capable client at ``https://<your-tino-host>/mcp`` (server is mounted at ``/mcp``).

With the `Claude Code <https://docs.claude.com/en/docs/claude-code>`_ CLI:

.. code-block:: console

    $ claude mcp add --transport http tino https://tino.example.com/mcp

.. hint::

  The CLI opens your browser for the OAuth login, then connects. 
  No token needs to be copied or configured by hand — the client identifies itself with a CIMD and obtains the token automatically.

Authentication
~~~~~~~~~~~~~~

MCP clients authenticate via **OAuth 2.0**, as documented in the :ref:`authentication <usage/authentication:MCP>` chapter.

Available tools
~~~~~~~~~~~~~~~

Each tool enforces the minimum :ref:`role <usage/buckets:Access control>` the user must hold on the target bucket:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Tool
     - Min. role
     - Description
   * - ``list_buckets``
     - —
     - List buckets the user can access, with their role and per-bucket instructions.
   * - ``list_files``
     - Viewer
     - List files and directories in a bucket.
   * - ``read_file``
     - Viewer
     - Read a file's text content.
   * - ``compile_typst``
     - Viewer
     - Compile a file and report success or the compiler error.
   * - ``git_status``
     - Viewer
     - Show the working-tree status of a bucket.
   * - ``git_log``
     - Viewer
     - Show commit history, optionally for a single file.
   * - ``write_file``
     - Editor
     - Create or overwrite a text file.
   * - ``delete_file``
     - Editor
     - Delete a file.
   * - ``rename_file``
     - Editor
     - Rename or move a file.
   * - ``create_dir``
     - Editor
     - Create an empty directory.
   * - ``rename_dir``
     - Editor
     - Rename or move a directory and its contents.
   * - ``delete_dir``
     - Editor
     - Delete a directory and all its contents.
   * - ``commit``
     - Committer
     - Commit changes to the bucket's git repository.

.. hint::

    The ``compile_typst`` tool lets an agent verify its own work: after editing a file it can compile, read the error, fix the source, and only ``commit`` once the document is valid.

Instructions
~~~~~~~~~~~~

MCP instructions let you control how AI agents interact with TINO.
They are included in the server's context so the agent sees them before it starts working.

Global instructions
^^^^^^^^^^^^^^^^^^^

| **Scope**
| Global instructions apply to every MCP session.

| **Configuration**
| Set the :attr:`TINO_MCP_INSTRUCTIONS <tino.config.TINO_MCP_INSTRUCTIONS>` environment variable to provide organisation-wide guidance.

| **Example usage**
| Define the communication style, terminology, or policies, e.g.:

- Use "we" instead of "I" in all documents.
- Don't assume anything; always ask the user first.
- Never commit without approval.

.. note::

  The text is appended to TINO's built-in instructions.

Per-bucket instructions
^^^^^^^^^^^^^^^^^^^^^^^

| **Scope**
| Per-bucket instructions apply to a single bucket.

| **Configuration**
| Edit them in the bucket settings dialog (:ref:`Bucket MCP instructions <usage/buckets:MCP instructions>`) or via the REST API (``mcp_instructions`` in the bucket metadata). They are stored in the bucket's ``.meta.yml`` and returned by the ``list_buckets`` tool so the agent sees them when it discovers available buckets.

| **Example usage**
| Describe the bucket's content, structure, and conventions, e.g.:

- Write all content in British English. 
- Place new customer-related documents in a ``customers/{customer name}/`` directory.
- Never modify files under ``templates/``.
