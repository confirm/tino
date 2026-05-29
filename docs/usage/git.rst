.. _Git:

🔀 Git
------

Every bucket is backed by a git repository.
Modified files are highlighted in the file tree with a status indicator.

Committing
~~~~~~~~~~

Click the **Commit** button to open the commit dialog.
Select the files to include, write a commit message, and submit.

.. note::

   Only users with the **Committer** role can commit changes.

.. hint::

   `Git LFS <https://git-lfs.com/>`_ is used to store binary files in Git.


Viewing history
~~~~~~~~~~~~~~~

- **Bucket history** — click the clock icon in the file panel header to browse all commits in the bucket.
- **File history** — click the clock icon in the status bar (bottom of the editor) to see commits for the current file.

The history dialog shows a list of commits on the left and the file tree of the selected commit on the right.
Click a file to view its content at that point in time.

Restoring files
~~~~~~~~~~~~~~~

In the history dialog, select a commit and a file, then click **Restore this file** to overwrite the working copy with the version from that commit.
