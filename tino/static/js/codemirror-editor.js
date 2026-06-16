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
  selectNextOccurrence,
  vim,
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
    this._vim = new Compartment()
    this._wrap = new Compartment()
    this._view = new EditorView({
      parent,
      state: this._buildState(''),
    })
  }

  /** Undo/redo history — always active, so Vim's `u`, Ctrl-r and Ctrl-Z agree. */

  static _historyExt() {
    return [history(), keymap.of(historyKeymap)]
  }

  /**
   * Bind or unbind a collaborative-editing extension (yCollab). Undo stays with
   * the always-on CM history (yCollab is configured without its own undo
   * manager), so Vim and Ctrl-Z share one consistent history.
   * @param {object|Array|null} ext - The collab extension(s), or null to clear.
   */

  setCollab(ext) {
    this._view.dispatch({ effects: this._collab.reconfigure(ext || []) })
  }

  /**
   * Enable or disable Vim keybindings (with the mode/command status bar).
   * @param {boolean} enabled - True to turn Vim mode on.
   */

  setVim(enabled) {
    this._view.dispatch({ effects: this._vim.reconfigure(enabled ? vim({ status: true }) : []) })
  }

  /**
   * Toggle soft line wrapping (default on).
   * @returns {boolean} The new wrap state — true when wrapping is enabled.
   */

  toggleLineWrap() {
    this._wrapOn = this._wrapOn === false
    this._view.dispatch({
      effects: this._wrap.reconfigure(this._wrapOn ? EditorView.lineWrapping : []),
    })
    return this._wrapOn
  }

  /** @returns {EditorView} The underlying CodeMirror view. */

  get view() {
    return this._view
  }

  _buildState(doc) {
    return EditorState.create({
      doc,
      extensions: [
        this._vim.of([]),
        this._wrap.of(EditorView.lineWrapping),
        lineNumbers(),
        drawSelection(),
        foldGutter(),
        codeFolding(),
        bracketMatching(),
        highlightSelectionMatches(),
        indentUnit.of('  '),
        EditorState.allowMultipleSelections.of(true),
        indentOnInput(),
        CodeMirrorEditor._historyExt(),
        this._collab.of([]),
        typst(),
        keymap.of([
          this._saveBinding(),
          CodeMirrorEditor._gotoLineBinding(),
          CodeMirrorEditor._selectNextBinding(),
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
    return { key: 'Mod-g', preventDefault: true, run: view => gotoLine(view) }
  }

  /*
   * Mod-d selects the next occurrence (multi-cursor). Always report the key as
   * handled so the browser's Mod-d (bookmark) is suppressed even when there is
   * no further occurrence — otherwise the bookmark dialog leaks through.
   */

  static _selectNextBinding() {
    return {
      key: 'Mod-d',
      preventDefault: true,
      run: view => {
        selectNextOccurrence(view)
        return true
      },
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
    this._view.dispatch({ effects: this._placeholder.reconfigure(placeholder(text || '')) })
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

  /**
   * Move the caret to the start of a 1-based line and scroll it into view.
   * Clamped to the document bounds, so out-of-range lines are safe.
   * @param {number} lineNumber - 1-based line to jump to.
   */

  goToLine(lineNumber) {
    const { doc } = this._view.state
    const clamped = Math.max(SINGLE_ITEM, Math.min(lineNumber, doc.lines))
    const line = doc.line(clamped)
    // eslint-disable-next-line id-length -- CodeMirror's scrollIntoView axis key
    const scroll = EditorView.scrollIntoView(line.from, { y: 'center' })
    this._view.dispatch({
      effects: scroll,
      selection: { anchor: line.from },
    })
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
