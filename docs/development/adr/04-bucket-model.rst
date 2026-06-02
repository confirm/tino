.. _ADR-04:

ADR-04: The bucket model
========================

Context
-------

TINO needed a way to organise documents.
The options ranged from a flat file system shared across all users, to a fully hierarchical folder tree, to isolated per-project repositories.

Decision
--------

Documents are organised into **buckets** — named, isolated workspaces.
Each bucket is an independent git repository with its own file tree, commit history, and access control list.
Users switch between buckets explicitly; there is no global file tree spanning multiple buckets.

Consequences
------------

**Positive**

- | **Isolation**
  | Each bucket is self-contained — its history, access rules, and files are independent of every other bucket.
- | **Per-bucket access control**
  | Viewer, editor, and committer roles are assigned at the bucket level, making fine-grained access policy straightforward.
- | **Clear ownership**
  | Buckets map naturally to projects, teams, or customers — easy to reason about who owns what.
- | **Independent history**
  | Commits, diffs, and restores are scoped to a single bucket, keeping history clean and relevant.

**Negative**

- | **No cross-bucket operations**
  | Files cannot be shared or referenced across buckets. 
  | Shared assets (e.g. a corporate logo) must be duplicated or managed via a Typst package.
- | **No hierarchy**
  | There is no concept of nested buckets or folders of buckets — a flat list of named workspaces is all that exists at the top level.
