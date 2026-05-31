import {
  Annotation,
  Compartment,
  EditorState,
  EditorView,
  bracketMatching,
  codeFolding,
  defaultKeymap,
  drawSelection,
  foldGutter,
  foldKeymap,
  gotoLine,
  highlightSelectionMatches,
  history,
  historyKeymap,
  indentOnInput,
  indentUnit,
  indentWithTab,
  keymap,
  lineNumbers,
  placeholder,
  searchKeymap,
} from './vendor/codemirror.js'
import { typst, typstKeymap } from './codemirror-typst.js'
import { SINGLE_ITEM } from './constants.js'

/**
 * Editor controller around a CodeMirror 6 EditorView. Owns the view, its
 * extensions, and the reconfigurable compartments (editable, placeholder,
 * collab binding, undo history), and exposes a small intention-revealing API
 * (content, selection, setContent, setEditable, setCollab, onChange, …) that
 * the rest of the app uses instead of reaching into CodeMirror directly. The
 * raw view is available via `.view` for transaction-level work (toolbar,
 * collab reconcile).
 */

/*
 * Annotation marking content set programmatically (setContent), so the update
 * listener can tell programmatic replacements from user edits and only emit
 * change notifications for the latter.
 */

const _programmatic = Annotation.define()

const _noop = () => null

export class CodeMirrorEditor {

  /**
   * @param {HTMLElement} parent - Host element to mount CM into.
   * @param {object} [opts]
   * @param {Function} [opts.onSave] - Called on Mod-s.
   * @param {Function} [opts.onCursor] - Called when the selection changes.
   * @param {Function} [opts.onChange] - Called on user (non-programmatic) edits.
   */

  constructor(parent, opts = {}) {
    this._parent = parent
    this._onSave = opts.onSave || _noop
    this._onCursor = opts.onCursor || _noop
    this._onChange = opts.onChange || _noop
    this._editable = new Compartment()
    this._placeholder = new Compartment()
    this._collab = new Compartment()
    this._history = new Compartment()
    this._view = new EditorView({
      parent,
      state: this._buildState(''),
    })
  }

  /** Local-undo history extension, active only when collab is not bound. */

  static _historyExt() {
    return [history(), keymap.of(historyKeymap)]
  }

  /**
   * Bind or unbind a collaborative-editing extension (yCollab). Collab brings
   * its own author-scoped undo, so the local history is swapped out while it
   * is active and restored when `ext` is null.
   * @param {object|Array|null} ext - The collab extension(s), or null to clear.
   */

  setCollab(ext) {
    this._view.dispatch({
      effects: [
        this._collab.reconfigure(ext || []),
        this._history.reconfigure(ext ? [] : CodeMirrorEditor._historyExt()),
      ],
    })
  }

  /** @returns {EditorView} The underlying CodeMirror view. */

  get view() {
    return this._view
  }

  _buildState(doc) {
    return EditorState.create({
      doc,
      extensions: [
        lineNumbers(),
        drawSelection(),
        foldGutter(),
        codeFolding(),
        bracketMatching(),
        highlightSelectionMatches(),
        indentUnit.of('  '),
        indentOnInput(),
        this._history.of(CodeMirrorEditor._historyExt()),
        this._collab.of([]),
        typst(),
        keymap.of([
          this._saveBinding(),
          CodeMirrorEditor._gotoLineBinding(),
          ...typstKeymap,
          indentWithTab,
          ...searchKeymap,
          ...foldKeymap,
          ...defaultKeymap,
        ]),
        this._editable.of(EditorView.editable.of(true)),
        this._placeholder.of(placeholder('')),
        EditorView.updateListener.of(update => this._onUpdate(update)),
      ],
    })
  }

  _saveBinding() {
    return {
      key: 'Mod-s',
      preventDefault: true,
      run: () => {
        this._onSave()
        return true
      },
    }
  }

  static _gotoLineBinding() {
    return {
      key: 'Mod-g',
      preventDefault: true,
      run: view => gotoLine(view),
    }
  }

  _onUpdate(update) {
    if (update.selectionSet || update.docChanged)
      this._onCursor()
    if (!update.docChanged)
      return
    const programmatic = update.transactions
      .some(tr => tr.annotation(_programmatic) === true)
    if (!programmatic)
      this._onChange()
  }

  // ── content ──

  /** @returns {string} The full document text. */

  get content() {
    return this._view.state.doc.toString()
  }

  /**
   * Replace the whole document programmatically (e.g. loading a file or
   * adopting synced collab content). Does not emit a change notification;
   * call signalChange() when such a replacement should be persisted.
   * @param {string} text - The new document content.
   */

  setContent(text) {
    const { length } = this._view.state.doc
    this._view.dispatch({
      annotations: [_programmatic.of(true)],
      changes: { from: 0, insert: text, to: length },
    })
  }

  /** @returns {{from: number, to: number}} The main selection range. */

  get selection() {
    const { from, to } = this._view.state.selection.main
    return { from, to }
  }

  /** @returns {{line: number, col: number}} 1-based caret line and column. */

  getCursorPosition() {
    const pos = this._view.state.selection.main.head
    const line = this._view.state.doc.lineAt(pos)
    return { col: pos - line.from + SINGLE_ITEM, line: line.number }
  }

  // ── view configuration ──

  /** @param {boolean} editable - Whether the user can edit the document. */

  setEditable(editable) {
    this._view.dispatch({
      effects: this._editable.reconfigure(EditorView.editable.of(editable)),
    })
  }

  /** @param {string} text - Placeholder shown when the document is empty. */

  setPlaceholder(text) {
    this._view.dispatch({
      effects: this._placeholder.reconfigure(placeholder(text || '')),
    })
  }

  /** @param {boolean} hidden - Toggle the host element's `hidden` class. */

  setHidden(hidden) {
    this._parent.classList.toggle('hidden', hidden)
  }

  /** @returns {boolean} True when the editor is hidden (binary preview shown). */

  get hidden() {
    return this._parent.classList.contains('hidden')
  }

  /** Move keyboard focus into the editor. */

  focus() {
    this._view.focus()
  }

  // ── change notifications ──

  /** @param {Function} fn - Called on each user (non-programmatic) edit. */

  onChange(fn) {
    this._onChange = fn || _noop
  }

  /** Emit a change notification for an externally applied content update. */

  signalChange() {
    this._onChange()
  }

}
