.. _ADR-03:

ADR-03: Git as the storage backend
==================================

Context
-------

TINO needs versioned document storage with history, diffing, and the ability to restore earlier states.
The options were:

- A custom version table in a database
- An object storage system with versioning
- `Git <https://git-scm.com/>`_

Decision
--------

Every bucket is a plain git repository on disk.
The Typst source files and assets are committed directly; ``.meta.yml`` (bucket metadata) lives in the same repo.
TINO uses `GitPython <https://gitpython.readthedocs.io/>`_ to drive git operations from the application layer.

Consequences
------------

**Positive**

- | **Full history**
  | Every change carries an author, timestamp, and commit message — for free.
- | **Standard operations**
  | Diff, restore, and branch are plain git commands, not custom application code.
- | **Large file support**
  | `Git LFS <https://git-lfs.com/>`_ is enabled to handle large binaries (images, fonts) without bloating the repository, resp. history.
- | **Efficient storage**
  | Git delta-compresses history, so storing many versions of text files costs very little disk space.
- | **No vendor lock-in**
  | Buckets are plain git repositories — migrating away from TINO leaves you with standard repos, not a proprietary format.
- | **Extensible foundation**
  | Should direct repository access ever be desired the infrastructure is already in place.
  | Git is a well-understood, widely supported interface to build on.

**Negative**

- | **Write serialisation**
  | The working tree and index must be managed carefully to avoid lock contention under concurrent writes — TINO serialises per-slug writes with a threading lock.
- | **Diverging working tree**
  | Collaboration auto-save writes bypass the normal commit flow; the working tree diverges from HEAD until the user explicitly commits.
