.. _Introduction:

💁🏻‍♂️ Introduction
====================

.. _Rationale:

🤷🏻‍♂️ Rationale
-----------------

Most of our business processes at `confirm IT <https://confirm.ch/>`_ are fully automated — infrastructure as code, CI/CD pipelines, reproducible deployments. About 99% of our work is treated as code: auditable, versioned, and automatable. Document production was the last holdout. We used Apple Pages for a while — more usable than O365, but still impossible to automate in any meaningful way.

The answer was obvious: treat documents the same way we treat everything else. In practice, that meant:

- Web-based and :ref:`self-hosted <Deployment>`
- :ref:`Version-controlled <Git>` with full history
- :ref:`Authentication <Authentication>` and authorisation via OpenID Connect
- :ref:`API <REST API>` for automation and integration
- Real-time :ref:`collaboration <Collaboration>`
- Reusable templates and corporate design as :ref:`packages <Packages>`

No existing tool ticked all the boxes. The first question was which document format to build on. `Markdown <https://en.wikipedia.org/wiki/Markdown>`_ and `reStructuredText <https://en.wikipedia.org/wiki/ReStructuredText>`_ lack the typographic control needed for polished deliverables. `LaTeX <https://en.wikipedia.org/wiki/LaTeX>`_ offers that control, but the learning curve makes it impractical for non-technical contributors.

`Typst <https://typst.app/>`_ struck the right balance — expressive enough for professional output, approachable enough for the whole team. Typst's own editor comes close to a complete solution and even offers a self-hosted variant — but while the compiler is open source, the web editor is a closed-source commercial product. We needed something we could fully control: open source, deeply integrated with our identity provider and git workflows, and extensible to our use cases.

So we built TINO: a collaborative, self-hosted editing platform around `Typst`_.

.. _Name:

🙅🏻‍♂️ TINO Is Not Office
----------------------------

**TINO** — pronounced *TEE-noh* (/ˈtiːnoʊ/) — is short for **TINO Is Not Office**.

Yes, the first word is *TINO* again. Expand it all the way and you get «TINO Is Not Office Is Not Office Is Not Office…», a sentence with no natural end — much like the formatting meetings it was built to replace. We're in proud company: GNU's Not Unix, WINE Is Not an Emulator, and TINO, with total conviction, Is Not Office – and that's a feature!

It is, we'll admit, a bit of an oxymoron. We built a tool whose entire job is producing letters, contracts and immaculate PDFs — the most office-coded work imaginable — and then named it *Not Office*. No ribbon. No "read-only, locked for editing by another user." No layout that quietly rearranges itself the moment a colleague opens it on a different laptop. Just versioned, collaborative text that compiles into something you'd actually be happy to send.

So TINO is *for* the office and, by name, *Not Office*. Both true. 

.. _Features:

✨ Features
-----------

The TINO editor ships with the following features out of the box:

- | **Inline SVG preview**
  | Live-rendered preview next to the :ref:`editor <Editor>`, updated on every change.
- | **PDF export**
  | Compile and download production-ready PDFs directly from the :ref:`editor <Editor>`.
- | **Real-time collaboration**
  | :ref:`Concurrent editing <Collaboration>` via CRDT over WebSockets. Changes merge automatically, no conflicts.
- | **Group-based access control**
  | Assign viewer, editor, or committer roles per :ref:`bucket <Buckets>`, backed by :ref:`OpenID Connect <Authentication>` group claims. 
- | **Git versioning**
  | Every bucket is a :ref:`Git <Git>` repository with built-in history, commits, and restore.
- | **Drag & drop uploads**
  | Drop :ref:`files <Files>` or ZIP archives into a bucket to import them. Archives are extracted automatically.
- | **Local packages**
  | Reusable templates and shared components as Typst :ref:`packages <Packages>`.
- | **Custom fonts**
  | Mount your own :ref:`font library <Fonts>` for consistent corporate typography.
- | **Minimal operations**
  | No database, no object storage. Just a filesystem and your identity provider.
- | **MCP server** *(experimental)*
  | Built-in :ref:`Model Context Protocol <MCP server>` server that lets AI agents list, read, write, compile, and commit Typst files — with the same access rules as a human user.
