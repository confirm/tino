.. _Collaboration:

🤝 Collaboration
----------------

Typarr edits are collaborative in real time. When two or more people open the
same file in a bucket, their changes are merged live and everyone works on the
same document as it evolves.

How it works
~~~~~~~~~~~~~

Each open file is backed by a shared CRDT (conflict-free replicated data type)
document synchronised over a WebSocket connection. Edits made by any participant
are merged automatically — there is no "save to see other people's changes" step
and no manual conflict resolution. When the last participant closes the file, its
content is flushed to disk.

Live editing is available to users with **editor** or **committer** access to a
bucket; viewers open files as a read-only copy.

Presence
~~~~~~~~

While others are editing the same file you see their **cursors and selections**
inline, each labelled with the collaborator's username. Every user is assigned a
colour computed from their username, so the same person consistently appears in
the same colour.

Connection handling
~~~~~~~~~~~~~~~~~~~~~

If the connection drops — for example when the server restarts — Typarr
reconnects automatically and re-synchronises the document. Any edits you make
while disconnected are preserved and replayed onto the latest server content
once the connection is restored.
