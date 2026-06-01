.. _Theming:

🎨 Theming
----------

Dark and light mode
~~~~~~~~~~~~~~~~~~~

Click the sun/moon icon in the toolbar to toggle between dark and light mode.
Your preference is saved in the browser and restored on the next visit.

Accent colour
~~~~~~~~~~~~~

The instance-wide accent colour is configured by the administrator via the :attr:`TYPARR_ACCENT_COLOUR <typarr.config.TYPARR_ACCENT_COLOUR>` environment variable.

Editor colours
~~~~~~~~~~~~~~

The editor's colours are theme-aware and follow the corporate-design palette,
adjusting automatically between dark and light mode:

* **Syntax highlighting** uses dedicated colours per token type, with separate
  steps tuned for the dark and light editor backgrounds.
* The **text-selection** highlight is a translucent tint of the configured
  accent colour.
* **Collaborator cursor** colours are computed from each username (see
  :ref:`Collaboration`), so they are stable per user.
