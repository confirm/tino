.. _Usage:

📖 Usage
========

This guide walks through the day-to-day use of the Typr editor.

.. _Authentication:

🔐 Authentication
-----------------

Typr uses OpenID Connect (OIDC) for authentication.
Click **Login with SSO** on the login page to be redirected to your identity provider.
After a successful login you are returned to the editor.

To sign out, click the **Logout** button in the top-right corner of the toolbar.

.. _Buckets:

🪣 Buckets
----------

Documents are organised into **buckets**.
Each bucket is a self-contained git repository that holds one or more Typst files.

Selecting a bucket
~~~~~~~~~~~~~~~~~~

Click the bucket button in the toolbar (top-left) to open the bucket picker.
Select a bucket from the list to load its files into the editor.

Creating a bucket
~~~~~~~~~~~~~~~~~

Administrators can create new buckets from the bucket picker dialog.
Click **New Bucket**, fill in a slug (the unique identifier) and an optional description, then save.

Access control
~~~~~~~~~~~~~~

Each bucket has its own access control list.
Entries map an OIDC group to one of three roles:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Role
     - Permissions
   * - **Viewer**
     - Browse files and view commit history.
   * - **Editor**
     - Everything a Viewer can do, plus create, edit, rename, and delete files.
   * - **Committer**
     - Everything an Editor can do, plus commit changes to the git repository.

Members of the configured admin groups (see :ref:`Configuration`) are implicitly treated as **Committer** on every bucket.

.. _Files:

📄 Files
--------

Creating files
~~~~~~~~~~~~~~

Click the **New file** button in the file panel header to create an empty file.
You will be prompted for a file name, including any path prefix (e.g. ``chapters/intro.typ``).

From template
~~~~~~~~~~~~~

Click the **New from template** button to initialise the bucket from a Typst template.
The dialog offers two tabs:

- **Custom** — templates from the local package directory.
- **Typst Universe** — templates from the public `Typst package registry <https://typst.app/universe>`_.

Uploading files
~~~~~~~~~~~~~~~

Drag and drop files from your desktop onto the file explorer panel.
If you drop onto a folder, the files are uploaded into that folder.

Renaming and deleting
~~~~~~~~~~~~~~~~~~~~~

Hover over a file or folder in the tree to reveal the **Rename** and **Delete** action buttons.

.. _Editor:

✏️ Editor
---------

Tabs
~~~~

Every opened file appears as a tab above the editor.
Click a tab to switch to it, or click the **×** button on a tab to close it.
Tabs are persisted across page reloads.

Formatting toolbar
~~~~~~~~~~~~~~~~~~

The toolbar above the editor provides common Typst formatting actions.
For the full syntax reference, see the `Typst documentation <https://typst.app/docs/reference/>`_.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Action
     - Typst syntax
     - Description
   * - Bold
     - :code:`*…*`
     - Wrap the selection in asterisks.
   * - Italic
     - :code:`_…_`
     - Wrap the selection in underscores.
   * - Heading
     - ``=``
     - Insert a heading prefix.
   * - Bullet list
     - ``-``
     - Start or continue a bullet list.
   * - Numbered list
     - ``+``
     - Start or continue a numbered list.
   * - Link
     - :code:`#link("…")`
     - Insert a link function call.
   * - Image
     - :code:`#image("…")`
     - Insert an image function call.
   * - Inline code
     - ````` `…` `````
     - Wrap the selection in backticks.
   * - Code block
     - ````` ```…``` `````
     - Wrap the selection in triple backticks.
   * - Math
     - :code:`$…$`
     - Wrap the selection in dollar signs.

Keyboard shortcuts
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Shortcut
     - Action
   * - :kbd:`Ctrl+S` / :kbd:`⌘S`
     - Save the current file.
   * - :kbd:`Tab`
     - Insert indentation.
   * - :kbd:`Enter`
     - Continue the current list (bullet or numbered).

Saving
~~~~~~

Files are **auto-saved** one second after you stop typing.
You can also save manually with the **Save** button or :kbd:`Ctrl+S`.
Unsaved files are marked with a dot on their tab.

.. _Preview:

👁 Preview
----------

The right-hand panel shows a live SVG preview of the current ``.typ`` file.
The preview is re-rendered automatically after each save.

Use the **Zoom in** / **Zoom out** buttons (or the displayed percentage) to adjust the preview scale.

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

Viewing history
~~~~~~~~~~~~~~~

- **Bucket history** — click the clock icon in the file panel header to browse all commits in the bucket.
- **File history** — click the clock icon in the status bar (bottom of the editor) to see commits for the current file.

The history dialog shows a list of commits on the left and the file tree of the selected commit on the right.
Click a file to view its content at that point in time.

Restoring files
~~~~~~~~~~~~~~~

In the history dialog, select a commit and a file, then click **Restore this file** to overwrite the working copy with the version from that commit.

.. _Theming:

🎨 Theming
----------

Dark and light mode
~~~~~~~~~~~~~~~~~~~

Click the sun/moon icon in the toolbar to toggle between dark and light mode.
Your preference is saved in the browser and restored on the next visit.

Accent colour
~~~~~~~~~~~~~

The instance-wide accent colour is configured by the administrator via the ``ACCENT_COLOUR`` environment variable (see :ref:`Configuration`).
It must match a colour family from the `confirm design system <https://assets.confirm.ch/colours.json>`_.
