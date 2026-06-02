.. _Architecture:

🏗️ Architecture
================

This document describes TINO's high-level architecture and links to the individual
Architecture Decision Records (ADRs) that explain key design choices.

.. _Components:

Components
----------

TINO is a single Python process (FastAPI) that serves both the REST/WebSocket API
and the static frontend. There is no separate frontend build step and no external
runtime dependencies beyond a filesystem and an optional OIDC provider.

.. mermaid::

    graph TD
        subgraph Browser
            JS[Vanilla JS]
            CM[CodeMirror 6]
            YC[Yjs CRDT client]
        end

        subgraph FastAPI
            R["REST routers<br/>auth · buckets · files · git · compile · …"]
            C["Collab<br/>Yjs room manager"]
        end

        FS[("Filesystem<br/>git repos")]
        T["Typst CLI<br/>subprocess"]
        O["OIDC provider<br/>optional"]

        Browser -->|HTTP / REST| R
        YC -->|WebSocket| C
        R --> FS
        C --> FS
        R --> T
        R --> O

.. _Storage Layout:

Storage layout
--------------

All persistent state lives on the filesystem — no database is required.

.. code-block:: text

    TINO_DATA_DIR/
    ├── buckets/                  ← TINO_BUCKET_DIR
    │   ├── <slug>/               ← one directory per bucket
    │   │   ├── .git/             ← full git repository
    │   │   ├── .meta.yml         ← bucket metadata (description, access rules)
    │   │   └── *.typ, img/, …   ← source files
    │   └── packages/             ← TINO_PACKAGE_DIR (local Typst packages)
    └── fonts/                    ← TINO_FONT_DIR (custom fonts)

.. _Request Lifecycle:

Request lifecycle
-----------------

A typical editing session follows this flow:

.. mermaid::

    sequenceDiagram
        actor User
        participant Browser
        participant FastAPI
        participant Collab as Yjs rooms
        participant Typst as Typst CLI
        participant FS as Filesystem

        User->>Browser: open TINO
        Browser->>FastAPI: GET /
        FastAPI-->>Browser: static frontend

        User->>Browser: log in
        Browser->>FastAPI: GET /oidc/login
        FastAPI-->>Browser: redirect → OIDC provider → session cookie

        User->>Browser: select bucket
        Browser->>FastAPI: GET /api/buckets
        FastAPI->>FS: list bucket dirs
        FastAPI-->>Browser: bucket list

        User->>Browser: open file
        Browser->>FastAPI: GET /api/buckets/{slug}/files/{path}
        FastAPI->>FS: read file
        FastAPI-->>Browser: file content

        Browser->>Collab: WS /api/buckets/{slug}/collab/{path}
        Collab->>FS: load saved state
        Collab-->>Browser: sync Yjs document

        User->>Browser: type
        Browser->>Collab: Yjs update (WebSocket)
        Collab-->>Browser: broadcast to other clients

        Note over Browser: auto-save debounce fires
        Browser->>FastAPI: PUT /api/buckets/{slug}/files/{path}
        FastAPI->>FS: write file

        Note over Browser: save triggers preview
        Browser->>FastAPI: GET /api/buckets/{slug}/compile/svg/{path}
        FastAPI->>Typst: typst compile --format svg
        Typst->>FS: read source + fonts
        Typst-->>FastAPI: SVG pages
        FastAPI-->>Browser: SVG pages

.. _ADRs:

Architecture Decision Records
------------------------------

.. toctree::
   :maxdepth: 1
   :glob:

   adr/*
