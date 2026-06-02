.. _ADR-02:

ADR-02: No database
===================

Context
-------

Most web applications use a (relational) database (PostgreSQL, SQLite, …) to store metadata, user state, and application data. 
The question was whether TINO should follow that convention.

Decision
--------

TINO stores all persistent state on the filesystem:

- **Bucket metadata** (description, access rules) lives in a ``.meta.yml`` file inside the bucket directory.
- **Source files** are plain files in the bucket.
- **Fonts** and **local packages** are files in configurable directories.
- **User sessions** are signed cookies — no server-side session store.

There is no database process, schema, migration, or connection pool.

.. note::

  The absence of a database is a deliberate design choice, not an oversight.
  If TINO's requirements ever outgrow the filesystem, introducing a database would be the natural next step — but that day has not come.

Consequences
------------

**Positive**

- | **Zero dependencies**
  | Deploy with a single container and a volume — no database process, schema, or connection pool.
- | **Simple backup**
  | Backup and restore are a plain filesystem copy, ``rsync`` or similar.
- | **Inspectable**
  | All state is readable and editable with standard tools (``cat``, ``git``, ``vim``).

**Negative**

- | **No rich querying**
  | Listing buckets iterates the directory. Acceptable at the scale TINO targets (tens to low hundreds of buckets).
- | **Manual write serialisation**
  | Per-slug write serialisation must be handled in application code (threading locks on ``BucketService``) rather than by the database.
- | **No cross-bucket transactions**
  | Atomic operations spanning multiple buckets are not possible.
