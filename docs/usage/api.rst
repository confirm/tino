.. _REST API:

🔌 REST API
-----------

TINO exposes a REST API that powers the web UI.
The same endpoints are available for scripting and automation.

Interactive API documentation is built in and served by every TINO instance:

- **Swagger UI** — ``/docs``
- **ReDoc** — ``/redoc``
- **OpenAPI schema** — ``/openapi.json``

Authentication
~~~~~~~~~~~~~~

Browser-based clients use the OIDC session cookie. Non-interactive clients —
scripts and CI — authenticate with an :ref:`API key <API keys>` instead.
