.. _Fonts:

🔤 Custom fonts
---------------

Typarr supports custom fonts for Typst compilations. Fonts placed in the
:attr:`TYPARR_FONT_DIR <typarr.config.TYPARR_FONT_DIR>` directory are
automatically available to all documents via the ``--font-path`` flag.

.. note::

    Supported formats: **TTF**, **OTF**, **WOFF**, **WOFF2**.

Managing fonts via the UI
~~~~~~~~~~~~~~~~~~~~~~~~~

Administrators can manage fonts directly from the toolbar:

1. Click the **font** icon in the top-right toolbar.
2. Click **Upload fonts** to add one or more font files.
3. Hover over a font and click the **delete** icon to remove it.

.. note::

    Font management is restricted to administrators.

Providing fonts via Docker
~~~~~~~~~~~~~~~~~~~~~~~~~~

Fonts can also be provided at container level without the UI, for example
via a bind mount:

.. code-block:: bash

    docker run -d \
        -e TYPARR_FONT_DIR=/fonts
        -v /fonts:/fonts \
        …

Or by adding them to the image at build time:

.. code-block:: dockerfile

    # Set environment variable so Typarr / Typst knows where to look for the fonts.
    ENV TYPARR_FONT_DIR=/fonts

    # Copy the fonts into the Docker image.
    COPY fonts/ /fonts
