TINO docs
=========

Welcome to the official documentation of TINO — a collaborative, self-hosted editing platform around `Typst <https://typst.app/>`_ documents, built for teams that want to author, review, and publish together.

.. image:: /_static/mascot2.svg
   :alt: TINO mascot
   :align: right
   :width: 280px

TINO sets out to do three things:

- | **Replace desktop word processors**
  | Move document production to the browser,
  | with version control and collaboration built in.
- | **Keep documents on your infrastructure**
  | Privacy-aware. Self-hosted by design. 
  | Nothing leaves your network.
- | **Empower the whole team**
  | `Typst`_ — powerful typesetting for professional output,
  | approachable for everyone.

Content
-------

.. raw:: html

   <div class="toc-columns">

.. toctree::
   :maxdepth: 1

   introduction
   vision
   support

.. toctree::
   :maxdepth: 1
   :caption: Operations

   operations/deployment
   operations/configuration
   operations/upgrade

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

.. raw:: html

   </div>

.. important::

   **TINO is not affiliated with** `Typst <https://typst.app/>`_. 

   `Typst`_ develops both the `open-source compiler <https://typst.app/open-source/>`_ and its own commercial web editor at `typst.app <https://typst.app/>`_. TINO would not exist without their open-source compiler — we are grateful for their work and the ecosystem they have created 👏🏻.

   Their editor is more polished, more feature-rich, and backed by commercial support — in many ways it is the better product. If you don't need self-hosting or deep integration with your own infrastructure, we genuinely recommend it — and using it directly supports the people who make the language we all benefit from. TINO exists for teams that require full control over where their documents live.

.. ifconfig:: todo_include_todos

   .. raw:: html

      <div style="clear: both;"></div>

   To-dos
   ------

   .. todolist::
