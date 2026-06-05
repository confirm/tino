.. _ADR-06:

ADR-06: Vanilla JS frontend
===========================

Context
-------

Modern web frontends typically use a component framework (React, Vue, Svelte, …).
The question was whether TINO's frontend warranted that dependency.

Decision
--------

The TINO frontend is written in plain ES2022 JavaScript with no build step and no framework.
The only significant runtime dependencies are `CodeMirror 6 <https://codemirror.net/>`_ (editor) and
`Yjs <https://yjs.dev/>`_ (collaboration), both bundled as a single pre-built vendor file. 
CSS is hand-written; no utility framework is used.

Consequences
------------

Positive
~~~~~~~~

- | **No build toolchain**
  | No npm, no bundler, no transpiler in the development loop. Edit a file, reload the browser.
- | **No framework churn**
  | The frontend does not rot when a framework releases a major version.
- | **Small payload**
  | The browser downloads and parses less JavaScript.
- | **Easy to navigate**
  | The codebase is accessible to contributors who are not frontend specialists.
- | **What you edit is what runs**
  | Files are served as-is — no source maps, no compilation artefacts, no discrepancy between the editor and the browser. Debugging is straightforward.
- | **AI-friendly**
  | Plain JS is an excellent foundation for AI-assisted development: no framework abstractions, no transpilation layer, and no generated code for the model to reason through — just files the AI can read, edit, and reload directly.

Negative
~~~~~~~~

- | **Manual DOM updates**
  | No reactive data binding — DOM updates are written by hand. Manageable at TINO's current UI complexity, but would become painful if the interface grew significantly.
- | **No component abstraction**
  | Shared UI patterns (dialogs, panels) are duplicated across files rather than encapsulated in reusable components.
