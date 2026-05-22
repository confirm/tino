.. _Introduction:

💁🏻‍♂️ Introduction
====================

.. _Purpose:

🎯 Purpose
----------

Typr is a self-hosted web editor for `Typst <https://typst.app/>`_ documents, built for teams that want to write, review, and publish together.

- | **Web-based word processing for technical documents**
  | Write and typeset documents from any browser — no local installation needed.
- | **Team editing without friction**
  | Multiple people work on the same document at once, no file locking or manual merging.
- | **Self-hosted and under your control**
  | Run Typr on your own infrastructure — your documents never leave your network.
- | **Nothing to install for end users**
  | Open a browser, pick a project, start writing. No desktop app, no plugins.
- | **Built on Typst**
  | Leverage the speed and expressiveness of `Typst <https://typst.app/>`_ for beautiful, reproducible output.

.. _Features:

✨ Features
-----------

The Typr editor ships with the following features out of the box:

- | **Inline SVG preview**
  | See a live-rendered preview of your document next to the editor, updated on every change.
- | **Real-time collaboration**
  | Concurrent editing via Yjs/CRDT over WebSockets — changes merge automatically, no conflicts.
- | **Git versioning**
  | Each project is a full git repository. View file status, commit changes, browse history, and restore earlier versions.
- | **Group-based access control**
  | Assign viewer, editor, or admin roles per project, backed by OpenID connect and group claims.
- | **No database required**
  | All state lives on the filesystem, in git, and in Keycloak — nothing else to operate.

.. _Rationale:

🤷🏻‍♂️ Rationale
-----------------

Most of our business processes are fully automated — but our word processing still relied on native desktop applications with templates hard to control.

We wanted «word processing as code»:

- Web-based and self-hosted
- Version-controlled documents
- Authentication and authorisation via OpenID Connect
- Real-time collaboration

Nothing on the market ticked all the boxes, so we decided to build our own.
That left the question of which document format to use.

Markdown and reStructuredText got us part of the way, but they lack the typographic control needed for polished deliverables. 
LaTeX offers that control, yet the learning curve and tooling overhead made it impractical for non-technical contributors.

`Typst <https://typst.app/>`_ struck the right balance — expressive enough for professional output, approachable enough for the whole team. 
The only thing missing was a collaborative, web-based editing platform we could run ourselves.

So we built Typr.
