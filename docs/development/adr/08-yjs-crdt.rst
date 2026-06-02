.. _ADR-08:

ADR-08: Yjs CRDT for real-time collaboration
============================================

Context
-------

TINO needs concurrent multi-user editing of the same file without conflicts.
The classic approaches are operational transformation (OT) — used by Google Docs — or conflict-free replicated data types (CRDTs).
A third option was to skip real-time collaboration entirely and rely on git merges.

Decision
--------

TINO uses `Yjs <https://yjs.dev/>`_ (a CRDT library) with a custom WebSocket server backed by `pycrdt <https://github.com/jupyter-server/pycrdt>`_ (the Python
Yjs binding).
CodeMirror 6's ``y-codemirror.next`` binding connects the editor state to the shared Yjs document.

Each open file gets a **room** on the server.
The server holds the authoritative document state in memory and syncs it to all connected clients.
Rooms are evicted after a configurable TTL (``TINO_ROOM_TTL``) of inactivity.

Consequences
------------

**Positive**

- | **Conflict-free merges**
  | Merges are automatic and instantaneous — no conflict dialogs, ever.
- | **Resilient to disconnects**
  | Works correctly with intermittent connectivity; clients re-sync seamlessly on reconnect.
- | **Awareness for free**
  | Collaborator cursors and presence (name, colour) come via the Yjs awareness protocol at no extra cost.
- | **Battle-tested**
  | The CRDT model is well-studied and Yjs is widely deployed in production.

**Negative**

- | **In-memory state**
  | The server holds live document state for each active room — memory usage scales with the number of concurrently open files.
- | **Lost on restart**
  | In-memory state is discarded on server restart; clients resync from the last saved file, losing any unsaved CRDT history.
- | **Native dependency**
  | ``pycrdt`` is a native extension that may complicate some deployment environments.
