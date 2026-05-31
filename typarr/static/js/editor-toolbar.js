import { SINGLE_ITEM } from './constants.js'

/**
 * Editor formatting toolbar for Typst markup shortcuts.
 *
 * Each action is applied as a CodeMirror transaction on the active editor
 * view: a `changes` spec plus the resulting `selection`. Because these are
 * ordinary (non-programmatic) transactions, the editor emits a change
 * notification and — under collaboration — propagates them automatically.
 */

const MAX_HEADING = 4

const HEADING_RE = /^(?<marks>={1,4}) /u

const LINK_PREFIX = '#link("'

const IMAGE_PREFIX = '#image("'

const CODE_FENCE = '```\n'

const TABLE_SNIPPET = '#table(\n  columns: 2,\n  [], [],\n  [], [],\n)'

const TABLE_CARET = '#table(\n  columns: 2,\n  ['

export class EditorToolbar {

  /** @param {TyparrApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._bar = document.getElementById('editor-toolbar')
  }

  /** Show the toolbar. */

  show() {
    this._bar.classList.remove('hidden')
  }

  /** Hide the toolbar. */

  hide() {
    this._bar.classList.add('hidden')
  }

  /** Bind click events for formatting buttons. */

  bind() {
    this._bar.addEventListener('click', evt => {
      const btn = evt.target.closest('[data-action]')
      if (btn)
        this._dispatch(btn.dataset.action)
    })
  }

  /** Route a button action to the right formatting method. */

  _dispatch(action) {
    switch (action) {
      case 'bold': this._wrap('*'); break
      case 'italic': this._wrap('_'); break
      case 'heading': this._cycleHeading(); break
      case 'bullet': this._prependLine('- '); break
      case 'numbered': this._prependLine('+ '); break
      case 'link': this._insertLink(); break
      case 'image': this._insertImage(); break
      case 'code': this._wrap('`'); break
      case 'codeblock': this._wrapBlock(); break
      case 'math': this._wrap('$'); break
      case 'table': this._insertTable(); break
      default: break
    }
  }

  /**
   * Wrap the selection (or insert an empty pair) with a symmetric delimiter,
   * placing the cursor between the delimiters when nothing is selected.
   */

  _wrap(char) {
    const ed = this.app.els.editor
    const { from, to } = ed.selection
    ed.view.dispatch({
      changes: [
        { from, insert: char },
        { from: to, insert: char },
      ],
      selection: { anchor: from + char.length, head: to + char.length },
    })
    ed.focus()
  }

  /**
   * Cycle heading level on the current line:
   * none → = → == → === → ==== → back to plain text.
   */

  _cycleHeading() {
    const ed = this.app.els.editor
    const pos = ed.selection.from
    const line = ed.view.state.doc.lineAt(pos)
    const result = EditorToolbar._nextHeading(line.text)
    ed.view.dispatch({
      changes: { from: line.from, insert: result.text, to: line.to },
      selection: { anchor: Math.max(0, pos + result.offset) },
    })
    ed.focus()
  }

  static _nextHeading(line) {
    const match = HEADING_RE.exec(line)
    if (!match)
      return { offset: '= '.length, text: `= ${line}` }
    const level = match.groups.marks.length
    if (level >= MAX_HEADING) {
      return {
        offset: -level - SINGLE_ITEM,
        text: line.slice(level + SINGLE_ITEM),
      }
    }
    const next = '='.repeat(level + SINGLE_ITEM)
    return {
      offset: SINGLE_ITEM,
      text: `${next} ${line.slice(level + SINGLE_ITEM)}`,
    }
  }

  /** Insert a prefix at the start of the current line. */

  _prependLine(prefix) {
    const ed = this.app.els.editor
    const pos = ed.selection.from
    const line = ed.view.state.doc.lineAt(pos)
    ed.view.dispatch({
      changes: { from: line.from, insert: prefix },
      selection: { anchor: pos + prefix.length },
    })
    ed.focus()
  }

  /** Insert a Typst link, using the selection as the display text if present. */

  _insertLink() {
    const ed = this.app.els.editor
    const { from, to } = ed.selection
    const snippet = `${LINK_PREFIX}")[${ed.content.slice(from, to)}]`
    ed.view.dispatch({
      changes: { from, insert: snippet, to },
      selection: { anchor: from + LINK_PREFIX.length },
    })
    ed.focus()
  }

  /** Insert a Typst image call with the cursor inside the path. */

  _insertImage() {
    const ed = this.app.els.editor
    const { from, to } = ed.selection
    ed.view.dispatch({
      changes: { from, insert: `${IMAGE_PREFIX}")`, to },
      selection: { anchor: from + IMAGE_PREFIX.length },
    })
    ed.focus()
  }

  /** Insert a Typst 2x2 table snippet with the cursor in the first cell. */

  _insertTable() {
    const ed = this.app.els.editor
    const { from, to } = ed.selection
    ed.view.dispatch({
      changes: { from, insert: TABLE_SNIPPET, to },
      selection: { anchor: from + TABLE_CARET.length },
    })
    ed.focus()
  }

  /** Wrap the selection in a fenced code block (``` … ```). */

  _wrapBlock() {
    const ed = this.app.els.editor
    const { from, to } = ed.selection
    const selected = ed.content.slice(from, to)
    ed.view.dispatch({
      changes: { from, insert: `${CODE_FENCE}${selected}\n\`\`\``, to },
      selection: {
        anchor: from + CODE_FENCE.length,
        head: from + CODE_FENCE.length + selected.length,
      },
    })
    ed.focus()
  }

}
