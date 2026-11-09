.. _Authentication:

🔐 Authentication
=================

OIDC
----

TINO uses OpenID Connect (OIDC) for authentication and interactive logins.

Click **Login with SSO** on the login page to be redirected to your identity provider.
After a successful login you are returned to the editor.

To sign out, click the **Logout** button in the top-right corner of the toolbar.

.. seealso::

    Also have a look at the :ref:`Access control <usage/buckets:Access control>`, and :ref:`OIDC integration <operations/deployment:oidc>`.


Groups
------

TINO uses user groups to drive :ref:`usage/buckets:Access control`. 

Group membership is not standardized by OpenID Connect (OIDC). Identity providers may expose groups through custom claims, provide them through the UserInfo response, or omit them entirely.

TINO combines claims from the ID token and the UserInfo endpoint. If your OIDC provider exposes group membership under a non-standard name, you can configure TINO to read it using :attr:`TINO_OIDC_GROUPS_CLAIM <tino.config.TINO_OIDC_GROUPS_CLAIM>`.

If your OIDC provider does not provide group membership, TINO can resolve groups locally instead.

Set :attr:`TINO_LOCAL_GROUPS <tino.config.TINO_LOCAL_GROUPS>` to ``true`` in the environment to bypass OIDC group resolution and use a ``.groups.yml`` file in the data directory.

The mapping supports exact email addresses, domain wildcards, and a global fallback. Matching entries are combined, so a user can inherit groups from multiple mappings:

.. code-block:: yaml
    
    # $DATA_DIR/.groups.yml
    # maps an email to a set of groups, supports wildcards
    '*':
      - all-users

    '*@acme.org':
      - employees

    wile.e.coyote@acme.org:
      - admins

    # Mr. Coyote is a member of 'all-users', 'employees', and 'admins'.

Local group resolution is intended for smaller deployments. For larger or enterprise deployments, we recommend using an identity broker such as Keycloak or Dex to normalize group membership and provide the required group claims to TINO.

API keys
--------

Interactive users sign in through the browser, but automation — CI pipelines and scripts — cannot complete the OIDC login flow.

For these clients TINO issues **API keys**: static bearer tokens that grant scoped access to the :ref:`REST API`.

.. note::

    Only token *hashes* are stored, so a leaked ``api_keys.yml`` exposes no usable credentials.

Creating a key
~~~~~~~~~~~~~~

Administrators manage keys from the **API Keys** button in the toolbar.

Click **New Key**, give it a descriptive label, and add one row per bucket and :ref:`role <usage/buckets:Access control>` the key may access.

.. important::

    On create the token is shown **once**.
    Copy it immediately, as it cannot be retrieved again.

Using a key
~~~~~~~~~~~

Send the token in the ``Authorization`` header of every request:

.. code-block:: console

    $ curl -H "Authorization: Bearer tino_…" \
        https://tino.example.com/api/buckets/<slug>/files

A key can only reach the buckets it was granted, with exactly the assigned role — independent of any OIDC group — and can never act as an administrator.

Revoking a key
~~~~~~~~~~~~~~

Open the **API Keys** dialog and delete the key.

MCP
---

The :ref:`MCP server <MCP server>` authenticates AI agents via **OAuth 2.0** using `CIMD <https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/>`_.

When an MCP client connects, it opens a browser for the user to log in via the same OIDC provider TINO already uses.
Every tool then runs **as that user** — the agent can only access buckets the user's group memberships allow.

.. important::

    MCP clients always authenticate via OAuth.
    The OIDC provider must be able to act as a `CIMD`_-capable MCP authorisation server (see :ref:`MCP integration <operations/deployment:mcp>`).

    Static :ref:`API keys <usage/authentication:API keys>` are deliberately **not accepted** by the MCP server — those are for automating the REST API.
