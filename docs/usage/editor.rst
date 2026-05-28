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

Preview
~~~~~~~

The right-hand panel shows a live SVG preview of the current ``.typ`` file.
The preview is re-rendered automatically after each save.

Use the **Zoom in** / **Zoom out** buttons (or the displayed percentage) to adjust the preview scale.
