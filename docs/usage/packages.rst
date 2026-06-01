.. _Packages:

📦 Local packages
-----------------

TINO supports local `Typst packages <https://github.com/typst/packages>`_ for
sharing reusable libraries and templates across buckets.

Local packages are stored in the :attr:`TINO_PACKAGE_DIR <tino.config.TINO_PACKAGE_DIR>`
directory, which defaults to a ``packages`` sub-directory inside the
:attr:`TINO_BUCKET_DIR <tino.config.TINO_BUCKET_DIR>`.

.. hint::

    When the package directory is inside the bucket directory (the default),
    it shows up as a regular bucket in the TINO UI and can be edited directly.

Package structure
~~~~~~~~~~~~~~~~~

Each package follows the Typst package layout::

    {PACKAGE_DIR}/{namespace}/{name}/{version}/typst.toml

For example, a package ``@local/mylib:1.0.0`` would be stored as::

    packages/
      local/
        mylib/
          1.0.0/
            typst.toml
            lib.typ

The ``typst.toml`` file contains the package metadata:

.. code-block:: toml

    [package]
    name        = "mylib"
    version     = "1.0.0"
    entrypoint  = "lib.typ"
    authors     = ["Your Name"]
    description = "A shared library for my team."

The ``entrypoint`` field points to the main ``.typ`` file that is loaded when the
package is imported.

Using a package
~~~~~~~~~~~~~~~

Once a package is in the package directory, any bucket can import it:

.. code-block:: typst

    #import "@local/mylib:1.0.0": *

The namespace (``local`` in this example) must match the directory name under
the package directory.

Creating a template
~~~~~~~~~~~~~~~~~~~

A package can also act as a template by adding a ``[template]`` section to
``typst.toml``:

.. code-block:: toml

    [package]
    name        = "mytemplate"
    version     = "1.0.0"
    entrypoint  = "package.typ"
    authors     = ["Your Name"]
    description = "My team's document template."

    [template]
    path       = "template"
    entrypoint = "main.typ"

- ``path`` is the directory containing the template files that are copied into a
  bucket when the template is initialised.
- ``entrypoint`` is the main ``.typ`` file inside that directory.

Template packages appear in the **Local** tab of the template picker when
creating a new bucket.
