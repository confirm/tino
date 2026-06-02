.. _ADR-07:

ADR-07: OIDC for authentication
===============================

Context
-------

TINO needed an authentication mechanism.
The options were: local auth (username/password with its own user store), LDAP, or SSO via OpenID Connect.

Decision
--------

TINO delegates authentication entirely to an external `OpenID Connect <https://openid.net/developers/how-connect-works/>`_ provider (e.g. `Keycloak <https://www.keycloak.org/>`_).
The OIDC callback establishes a signed server-side session cookie.
Group claims from the ID token drive :ref:`bucket-level access control <Buckets>`.

Authentication can be disabled entirely via ``TINO_AUTH_DISABLED`` for local development or trusted internal deployments.

Consequences
------------

**Positive**

- | **No user management**
  | TINO has no user database, no password storage, and no account lifecycle to manage — all of that lives in the identity provider.
- | **SSO out of the box**
  | Users who are already signed into the OIDC provider get seamless access.
- | **Group-based access control**
  | OIDC group claims map directly to bucket roles, making access policy a configuration concern rather than an application concern.
- | **Secure by delegation**
  | MFA, password policy, and session management are handled by a dedicated, audited identity system.
- | **De-facto standard**
  | OIDC is the standard authentication protocol for most enterprises and cloud platforms.
  | Chances are the identity provider is already in place and TINO just plugs in.

**Negative**

- | **External dependency**
  | A production deployment requires a running OIDC provider. 
  | This adds operational complexity for teams that do not already have one.
- | **Provider-specific claims**
  | Group claim names vary between providers (e.g. Keycloak vs Azure AD).
  | The claim key must be configured via ``TINO_OIDC_GROUPS_CLAIM``.
