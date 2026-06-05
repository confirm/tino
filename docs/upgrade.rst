.. _Upgrade:

⬆️ Upgrade
==========

This page lists the **actions required** when upgrading TINO between versions —
configuration changes, renamed variables, and anything that needs attention before or after pulling a new image.

It is not a full changelog; only changes that ask something of you are recorded here.

.. important::

  Review this page before upgrading.
  Some releases add **required** settings that TINO refuses to start without, so an upgrade can otherwise fail at boot.

main
----

``TINO_BASE_URL`` is now required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TINO no longer derives its public address from the incoming request and reverse-proxy headers.
You must set :attr:`TINO_BASE_URL <tino.config.TINO_BASE_URL>` to the externally reachable URL of your instance, e.g. ``https://tino.example.com``.

``TINO_TRUSTED_PROXIES`` has been **removed**, so you can drop it from your configuration.

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
