.. _ADR-01:

ADR-01: Typst as the document format
====================================

Context
-------

TINO needed a document format that could produce professional, print-ready output while being suitable for automation and accessible to non-technical contributors.
The candidates were:

- Markdown
- reStructuredText
- LaTeX
- Typst

Decision
--------

TINO is built around `Typst <https://typst.app/>`_ exclusively, using the official Rust-based compiler — not any third-party TypeScript reimplementation.
The Typst CLI is invoked as a subprocess for compilation to PDF and SVG (preview).

Consequences
------------

**Positive**

- | **Typographic control**
  | Typst produces publication-quality output — page layout, headers and footers, tables, math, citations — without the complexity of LaTeX.

- | **Approachable syntax**
  | The learning curve is shallow enough for the whole team, not just developers.

- | **Fast compilation**
  | Typst's incremental compiler is significantly faster than LaTeX, making live preview practical.

- | **Package ecosystem**
  | `Typst Universe <https://typst.app/universe>`_ provides reusable templates. 
  | TINO also supports :ref:`local packages <Packages>` for templates, corporate design, and much more.

- | **AI-friendly target**
  | Typst's clean, structured syntax makes it a practical output format for language-model-driven document generation (see :ref:`Rationale`).

**Negative**

- | **CLI coupling**
  | TINO is tightly coupled to the Typst CLI binary — a breaking change in its interface requires a TINO update.
- | **No migration path**
  | Teams already invested in LaTeX or Markdown cannot reuse existing documents without conversion.
- | **Younger ecosystem**
  | Typst is younger than LaTeX. Some specialised packages available in TeX do not yet have equivalents.
