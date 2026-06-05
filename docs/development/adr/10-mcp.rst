.. _ADR-10:

ADR-10: MCP server
==================

Context
-------

TINO's :ref:`vision <AI integration>` is to make document production a first-class participant in AI workflows.
The `Model Context Protocol <https://modelcontextprotocol.io/>`_ (MCP) has emerged as the standard way to expose an application's capabilities as tools an AI model can call.

Two questions had to be answered:

1. **Location**: Where should the MCP server live?
2. **Authentication**: How do AI clients authenticate?

For authentication specifically, the MCP specification builds on OAuth 2.0, and clients such as Claude do not support arbitrary static-token schemes.
They discover an authorization server and obtain a ``client_id`` through one of two mechanisms:

- `Client ID Metadata Document <https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/>`_ (CIMD): the ``client_id`` is an HTTPS URL the authorization server dereferences, so no client registration is needed.
- `Dynamic Client Registration <https://datatracker.ietf.org/doc/html/rfc7591>`_ (DCR): the client registers itself with the authorization server at runtime and receives a ``client_id`` in return.

Decision
--------

TINO embeds the MCP server in the main FastAPI process as a Streamable HTTP sub-application mounted at ``/mcp``, reusing the existing :ref:`services <Architecture>` and :ref:`access model <Access control>`.

For authentication, TINO acts as an **OAuth 2.0 Resource Server** and delegates authentication entirely to the same `OpenID Connect <https://openid.net/developers/how-connect-works/>`_ provider used for the web UI (:ref:`ADR-07`).
Authorization and the per-bucket access model (:ref:`ADR-04`) remains TINO's.

Clients discover the provider from TINO's protected-resource metadata, identify themselves with a CIMD, and complete an authorization-code flow with PKCE.
TINO validates the resulting access token against the provider's signing keys and runs each tool as the authenticated user, so group-based bucket access applies unchanged.

The protocol itself is handled by the official `MCP Python SDK <https://github.com/modelcontextprotocol/python-sdk>`_ rather than a hand-rolled implementation.

.. note::

  Several alternatives were considered and explicitly rejected during the evaluation, such as:

  | **TINO as its own AS (OAuth proxy)**
  | Many applications today embed a small authorization server that accepts CIMD from MCP clients and proxies authentication to the real identity provider. This is a pragmatic workaround because most providers do not support CIMD natively yet. However, it inverts TINO's role, pulls token issuance into the application, and duplicates what the provider already does. Keeping TINO a pure resource server is simpler and keeps a single source of identity.

  | **DCR instead of CIMD**
  | Dynamic Client Registration is supported by more providers today, but every MCP session creates a new client record in the provider's database. Over time this pollutes the client registry with a large number of abandoned entries that are never cleaned up. CIMD avoids this entirely — the client identifies itself via a URL, no state is written, and nothing accumulates.

  | **Static API keys**
  | MCP clients such as Claude do not support static token authentication, as they expect a standard OAuth flow. Static :ref:`API keys` therefore serve a different purpose (automating the REST API from CI) and are not accepted by the MCP server.

Consequences
------------

Positive
~~~~~~~~

- | **One access model**
  | MCP tools reuse the same services and group-based authorization as the REST API.
  | There is no second permission system to keep in sync.
- | **True user context**
  | Authentication tokens are issued to real users.
  | An agent inherits exactly the bucket roles of the person who authorised it.
- | **Standard protocol**
  | Any MCP-capable client (e.g. Claude) connects out of the box. TINO does not dictate the client.
- | **No new secrets**
  | Authentication and token issuance are the identity provider's job.
  | TINO stores no MCP credentials and issues no tokens of its own.
- | **Single process**
  | The server is mounted into the existing FastAPI app (see :ref:`ADR-05 <ADR-05>`).
  | No extra deployment or runtime to operate.

Negative
~~~~~~~~

- | **Provider must support CIMD**
  | The identity provider has to act as a CIMD-capable MCP authorization server.
  | CIMD is an emerging and still-experimental OAuth 2.0 / MCP capability.
- | **Discovery metadata proxy** 
  | Keycloak does not advertise the required ``"none"`` in ``token_endpoint_auth_methods_supported``.
  | TINO must work around this by proxying the authorization server metadata and injecting the missing value into the ``token_endpoint_auth_methods_supported`` (see `tino#23 <https://github.com/confirm/tino/issues/23>`_).
  | This adds complexity, and authentication logic which shouldn't be part of TINO.
  | The proxy can be removed once `keycloak#49730 <https://github.com/keycloak/keycloak/issues/49730>`_ is resolved upstream.
- | **Maturing ecosystem**
  | Both the CIMD draft and MCP OAuth client support are still stabilising.
  | Interoperability can vary between versions and vendors.
- | **Audience binding is provider-specific**
  | Strict resource-audience validation depends on how the provider maps audiences onto issued tokens, and must be configured there rather than in TINO.

.. note::

  The negative points above are largely a matter of timing.
  CIMD, DCR, and MCP OAuth support are all under active development with strong industry momentum.
  As these drafts mature into stable standards and identity providers adopt them, the interoperability concerns will diminish on their own.
