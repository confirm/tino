.. _Introduction:

💁🏻‍♂️ Introduction
====================

.. _Rationale:

🤷🏻‍♂️ Rationale
-----------------

Most of our business processes at `confirm IT <https://confirm.ch/>`_ are fully automated — but document production still relied on native desktop applications with templates that were hard to control and impossible to version.

We wanted «document authoring as code», meaning:

- Web-based and self-hosted
- Version-controlled with full history
- Authentication and authorisation via OpenID Connect
- Real-time collaboration
- Reusable templates and corporate design as packages

No existing tool ticked all the boxes. Typst's own editor comes close, but it's a hosted service — our documents had to stay on our own infrastructure.

That left the question of which document format to build on. `Markdown <https://en.wikipedia.org/wiki/Markdown>`_ and `reStructuredText <https://en.wikipedia.org/wiki/ReStructuredText>`_ lack the typographic control needed for polished deliverables. `LaTeX <https://en.wikipedia.org/wiki/LaTeX>`_ offers that control, but the learning curve makes it impractical for non-technical contributors.

`Typst <https://typst.app/>`_ struck the right balance — expressive enough for professional output, approachable enough for the whole team. 

So we built TINO: a collaborative, self-hosted editing platform around `Typst`_.

.. _Name:

🙅🏻‍♂️ TINO Is Not Office
----------------------------

**TINO** — pronounced *TEE-noh* (/ˈtiːnoʊ/) — is short for **TINO Is Not Office**.

Yes, the first word is *TINO* again. Expand it all the way and you get «TINO Is Not Office Is Not Office Is Not Office…», a sentence with no natural end — much like the formatting meetings it was built to replace. We're in proud company: GNU's Not Unix, WINE Is Not an Emulator, and TINO, with total conviction, Is Not Office – and that's a feature!

It is, we'll admit, a bit of an oxymoron. We built a tool whose entire job is producing letters, contracts and immaculate PDFs — the most office-coded work imaginable — and then named it *Not Office*. No ribbon. No "read-only, locked for editing by another user." No layout that quietly rearranges itself the moment a colleague opens it on a different laptop. Just versioned, collaborative text that compiles into something you'd actually be happy to send.

So TINO is *for* the office and, by name, *Not Office*. Both true. 

.. _Purpose:

🎯 Purpose
----------

TINO is a self-hosted web editor for `Typst`_ documents, built for teams that want to author, review, and publish together.

- | **Replace desktop word processors**
  | Move document production to the browser, with version control and collaboration built in.
- | **Keep documents on your infrastructure**
  | Privacy-aware. Self-hosted by design. Nothing leaves your network.
- | **Empower the whole team**
  | `Typst`_ – powerful typesetting for professional output, approachable for everyone.

.. _Features:

✨ Features
-----------

The TINO editor ships with the following features out of the box:

- | **Inline SVG preview**
  | Live-rendered preview next to the editor, updated on every change.
- | **PDF export**
  | Compile and download production-ready PDFs directly from the editor.
- | **Real-time collaboration**
  | Concurrent editing via CRDT over WebSockets. Changes merge automatically, no conflicts.
- | **Group-based access control**
  | Assign viewer, editor, or committer roles per bucket, backed by OpenID Connect group claims.
- | **Git versioning**
  | Every bucket is a git repository with built-in history, commits, and restore.
- | **Drag & drop uploads**
  | Drop files or ZIP archives into a bucket to import them. Archives are extracted automatically.
- | **Local packages**
  | Reusable templates and shared components as Typst packages.
- | **Custom fonts**
  | Mount your own font library for consistent corporate typography.
- | **Minimal operations**
  | No database, no object storage. Just a filesystem and your identity provider.
