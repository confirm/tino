.. _Deployment:

🚀 Deployment
=============

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
        -e OIDC_CLIENT_ID=typr \
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
