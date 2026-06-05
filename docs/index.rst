TINO
======

Welcome to the official documentation of TINO - a collaborative, self-hosted editing platform around `Typst <https://typst.app/>`_.
Built for teams that want to author, review, and publish together.

.. important::

   **TINO is not affiliated with** `Typst <https://typst.app/>`_. 

   `Typst`_ develops both the `open-source compiler <https://typst.app/open-source/>`_ and its own commercial web editor at `typst.app <https://typst.app/>`_. TINO would not exist without their open-source compiler — we are grateful for their work and the ecosystem they have created 👏🏻.

   Their editor is more polished, more feature-rich, and backed by commercial support — in many ways it is the better product. If you don't need self-hosting or deep integration with your own infrastructure, we genuinely recommend it — and using it directly supports the people who make the language we all benefit from. TINO exists for teams that require full control over where their documents live.

.. toctree::
   :maxdepth: 1

   introduction
   vision
   deployment
   configuration
   upgrade
   support

.. toctree::
   :maxdepth: 1
   :caption: Usage

   usage/authentication
   usage/buckets
   usage/files
   usage/editor
   usage/collaboration
   usage/git
   usage/packages
   usage/fonts
   usage/theming
   usage/api
   usage/mcp

.. toctree::
   :maxdepth: 1
   :caption: Development

   development/architecture
   development/setup

.. toctree::
   :maxdepth: 1
   :caption: Python API

   api/app
   api/models
   api/auth
   api/collab
   api/mcp_server
   api/middleware
   api/services
   api/routers


.. ifconfig:: todo_include_todos

   .. raw:: html

      <div style="clear: both;"></div>

   To Do's
   -------

   .. todolist::
