.. _Editor:

✏️ Editor
---------

TINO's editor is built on `CodeMirror 6 <https://codemirror.net/>`_ and
offers Typst-aware syntax highlighting, structural indentation, search and
navigation, code folding, and optional Vim keybindings.

Tabs
~~~~

Every opened file appears as a tab above the editor.
Click a tab to switch to it, or click the **×** button on a tab to close it.
Use **Close all tabs** to clear them all at once.
Tabs are persisted across page reloads.

Syntax highlighting
~~~~~~~~~~~~~~~~~~~~~

``.typ`` files are highlighted with a Typst-aware grammar: comments, strings,
keywords (``#let``, ``#show``, ``#import``, …), function calls, headings,
strong and emphasis, math, labels and references, numbers, and punctuation each
get their own colour. The palette is drawn from the corporate-design colours
and adapts to the active :ref:`theme <Theming>` (dark and light).

Formatting toolbar
~~~~~~~~~~~~~~~~~~~~

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
     - Cycle the current line's heading level (``=`` → ``==`` → ``===`` → ``====`` → plain text).
   * - Bullet list
     - ``-``
     - Start a bullet list on the current line.
   * - Numbered list
     - ``+``
     - Start a numbered list on the current line.
   * - Link
     - :code:`#link("…")`
     - Insert a link function call.
   * - Image
     - :code:`#image("…")`
     - Insert an image function call.
   * - Table
     - :code:`#table(…)`
     - Insert a 2×2 table skeleton.
   * - Inline code
     - ````` `…` `````
     - Wrap the selection in backticks.
   * - Code block
     - ````` ```…``` `````
     - Wrap the selection in triple backticks.
   * - Math
     - :code:`$…$`
     - Wrap the selection in dollar signs.

Indentation
~~~~~~~~~~~

The editor indents structurally. Pressing :kbd:`Enter` keeps the surrounding
indentation, adds a level after an opening bracket (``(``, ``[`` or ``{``), and
a line that begins with a closing bracket snaps back to match its opener. Plain
prose is left at its current indentation.

Lists continue automatically: pressing :kbd:`Enter` on a list item starts the
next item (numbered markers increment), while pressing :kbd:`Enter` on an empty
item ends the list.

Keyboard shortcuts
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Shortcut
     - Action
   * - :kbd:`Ctrl+S` / :kbd:`⌘S`
     - Save the current file.
   * - :kbd:`Ctrl+Z` / :kbd:`Ctrl+Y`
     - Undo / redo.
   * - :kbd:`Tab` / :kbd:`Shift+Tab`
     - Indent / dedent.
   * - :kbd:`Enter`
     - New line with structural indentation; continue a list.
   * - :kbd:`Ctrl+F` / :kbd:`⌘F`
     - Open the search panel (find & replace, with match-case / regexp / by-word options).
   * - :kbd:`F3` / :kbd:`Shift+F3`
     - Find next / previous.
   * - :kbd:`Ctrl+G` / :kbd:`⌘G`
     - Go to line.
   * - :kbd:`Ctrl+D` / :kbd:`⌘D`
     - Select the next occurrence of the selection (multi-cursor).

Folding and brackets
~~~~~~~~~~~~~~~~~~~~~~

Collapse a ``{…}`` or ``[…]`` block from the fold gutter beside the line
numbers, and click again to expand it. When the cursor sits next to a bracket,
its matching partner is highlighted.

Vim mode
~~~~~~~~

Click **Vim** in the toolbar to enable Vim keybindings. A status bar at the
bottom of the editor shows the current mode and ``:`` command line, and the
caret becomes a block cursor in normal mode. The setting is remembered per
browser — click **Vim** again to return to the default editing mode.

The usual motions and operators apply; ``u`` / :kbd:`Ctrl+R` undo and redo, and
``:w`` saves the file.

Saving
~~~~~~

Files are **auto-saved** a short moment after you stop typing — by default
250 ms, configurable via
:attr:`TINO_SAVE_DEBOUNCE_MS <tino.config.TINO_SAVE_DEBOUNCE_MS>`.
You can also save manually with the **Save** button, :kbd:`Ctrl+S`, or ``:w`` in
Vim mode. Unsaved files are marked with a dot on their tab.

Preview
~~~~~~~

The right-hand panel shows an SVG preview of the current ``.typ`` file.
The preview is re-rendered automatically after each save.

Use the **Zoom in** / **Zoom out** buttons (or the displayed percentage) to adjust the preview scale.
