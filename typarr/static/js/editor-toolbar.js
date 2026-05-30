import { INDEX_NOT_FOUND, SINGLE_ITEM } from './constants.js'

/**
 * Editor formatting toolbar for Typst markup shortcuts.
 * Provides wrap, line-prefix, and snippet insertion actions.
 */

const MAX_HEADING = 4

const HEADING_RE = /^(?<marks>={1,4}) /u

const LINK_PREFIX = '#link("'

const IMAGE_PREFIX = '#image("'

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
   * Wrap the selection (or insert an empty pair) with a
   * symmetric delimiter character.
   */

  _wrap(char) {
    const ed = this.app.els.editor
    const start = ed.selectionStart
    const end = ed.selectionEnd
    const wrapped = char + ed.value.slice(start, end) + char
    ed.setRangeText(wrapped, start, end)
    ed.selectionStart = start + char.length
    ed.selectionEnd = end + char.length
    EditorToolbar._afterEdit(ed)
  }

  /**
   * Cycle heading level on the current line:
   * none → = → == → === → ==== → back to plain text.
   */

  _cycleHeading() {
    const ed = this.app.els.editor
    const pos = ed.selectionStart
    const { lineStart, lineEnd } =
      EditorToolbar._lineRange(ed.value, pos)
    const line = ed.value.slice(lineStart, lineEnd)
    const result = EditorToolbar._nextHeading(line)
    ed.setRangeText(result.text, lineStart, lineEnd)
    ed.selectionStart = pos + result.offset
    ed.selectionEnd = ed.selectionStart
    EditorToolbar._afterEdit(ed)
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

  static _lineRange(text, pos) {
    const lineStart =
      text.lastIndexOf('\n', pos + INDEX_NOT_FOUND) + SINGLE_ITEM
    const idx = text.indexOf('\n', pos)
    const lineEnd = idx === INDEX_NOT_FOUND ? text.length : idx
    return { lineEnd, lineStart }
  }

  /** Insert a prefix at the start of the current line. */

  _prependLine(prefix) {
    const ed = this.app.els.editor
    const pos = ed.selectionStart
    const lineStart =
      ed.value.lastIndexOf('\n', pos + INDEX_NOT_FOUND) + SINGLE_ITEM
    ed.setRangeText(prefix, lineStart, lineStart)
    ed.selectionStart = pos + prefix.length
    ed.selectionEnd = pos + prefix.length
    EditorToolbar._afterEdit(ed)
  }

  /**
   * Insert a Typst link, using the selection as the display
   * text if present.
   */

  _insertLink() {
    const ed = this.app.els.editor
    const start = ed.selectionStart
    const selected = ed.value.slice(start, ed.selectionEnd)
    const snippet = `${LINK_PREFIX}")[${selected}]`
    ed.setRangeText(snippet, start, ed.selectionEnd)
    ed.selectionStart = start + LINK_PREFIX.length
    ed.selectionEnd = ed.selectionStart
    EditorToolbar._afterEdit(ed)
  }

  /** Insert a Typst image call with the cursor inside the path. */

  _insertImage() {
    const ed = this.app.els.editor
    const pos = ed.selectionStart
    const snippet = `${IMAGE_PREFIX}")`
    ed.setRangeText(snippet, pos, ed.selectionEnd)
    ed.selectionStart = pos + IMAGE_PREFIX.length
    ed.selectionEnd = ed.selectionStart
    EditorToolbar._afterEdit(ed)
  }

  /** Insert a Typst 2x2 table snippet with the cursor in the first cell. */

  _insertTable() {
    const ed = this.app.els.editor
    const pos = ed.selectionStart
    const snippet = '#table(\n  columns: 2,\n  [], [],\n  [], [],\n)'
    ed.setRangeText(snippet, pos, ed.selectionEnd)
    const cursor = pos + '#table(\n  columns: 2,\n  ['.length
    ed.selectionStart = cursor
    ed.selectionEnd = cursor
    EditorToolbar._afterEdit(ed)
  }

  /** Wrap the selection in a fenced code block (``` … ```). */

  _wrapBlock() {
    const ed = this.app.els.editor
    const start = ed.selectionStart
    const end = ed.selectionEnd
    const selected = ed.value.slice(start, end)
    const snippet = `\`\`\`\n${selected}\n\`\`\``
    ed.setRangeText(snippet, start, end)
    ed.selectionStart = start + '```\n'.length
    ed.selectionEnd = start + '```\n'.length + selected.length
    EditorToolbar._afterEdit(ed)
  }

  /** Restore focus and fire an input event after editing. */

  static _afterEdit(ed) {
    ed.focus()
    ed.dispatchEvent(new Event('input'))
  }

}
