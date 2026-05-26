import {
  INDEX_NOT_FOUND,
  ISO_DATETIME_LEN,
  SINGLE_ITEM,
  TAB_SPACES,
  escapeHtml,
} from './constants.js'

const LIST_RE = /^\s*[-+] /u

/**
 * Handles low-level editor textarea interactions:
 * key bindings, line numbers, cursor position, tabs, and status bar.
 */

export class EditorInput {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  /** Bind editor keyboard and input events. */

  bind() {
    const ed = this.app.els.editor
    const ln = this.app.els.lineNumbers
    ed.addEventListener('keydown', evt => this._handleKeydown(evt, ed))
    ed.addEventListener('input', () => this._handleInput())
    ed.addEventListener('scroll', () => {
      ln.scrollTop = ed.scrollTop
    })
    ed.addEventListener('click', () => this.updateCursorPos())
    ed.addEventListener('keyup', () => this.updateCursorPos())
  }

  /** Rebuild the tab bar, marking dirty files. */

  renderTabs() {
    const bar = this.app.els.tabBar
    bar.innerHTML = ''
    this.app.openTabs.forEach(tabPath => {
      this._renderTab(bar, tabPath)
    })
  }

  _renderTab(bar, tabPath) {
    const div = document.createElement('div')
    const isActive = tabPath === this.app.currentFile
    div.className = `tab${isActive ? ' active' : ''}`
    div.dataset.file = tabPath
    const isDirty = this.app.dirty.has(tabPath)
    const dirtyIcon =
      '<span class="material-symbols-outlined tab-icon-dirty">' +
      'edit</span>'
    const closeBtn =
      '<button class="tab-close" title="Close">&times;</button>'
    const icon = isDirty ? dirtyIcon : closeBtn
    div.innerHTML = `${icon}<span>${escapeHtml(tabPath)}</span>`
    bar.appendChild(div)
  }

  /** Highlight the active file in the tree. */

  highlightFileItem(path) {
    this.app.els.fileTree
      .querySelectorAll('.file-item')
      .forEach(el => {
        el.classList.toggle(
          'active', el.dataset.file === path,
        )
      })
  }

  /** Recalculate line numbers in the editor gutter. */

  updateLineNumbers() {
    const count = this.app.els.editor.value.split('\n').length
    const lines = Array.from(
      { length: count },
      (unused, idx) => idx + SINGLE_ITEM,
    )
    this.app.els.lineNumbers.textContent =
      `${lines.join('\n')}\n`
  }

  /** Update the cursor position display. */

  updateCursorPos() {
    const val = this.app.els.editor.value
    const pos = this.app.els.editor.selectionStart
    const lines = val.substring(0, pos).split('\n')
    const last = lines.length - SINGLE_ITEM
    const col = lines[last].length + SINGLE_ITEM
    this.app.els.cursorPos.textContent =
      `Ln ${lines.length}, Col ${col}`
  }

  /** Show the file's last-modified timestamp in the status bar. */

  updateStatusBar() {
    const el = this.app.els.statusBarModified
    const mtime = this.app.fileMtimes[this.app.currentFile]
    if (!mtime) {
      el.textContent = ''
      return
    }
    const date = new Date(mtime)
    el.textContent =
      `Modified ${date.toISOString().slice(0, ISO_DATETIME_LEN).replace('T', ' ')}`
  }

  // ── Internal ──

  _handleKeydown(evt, ed) {
    if (evt.key === 'Tab')
      EditorInput._insertTab(evt, ed)
    else if (evt.key === 'Enter')
      EditorInput._continueList(evt, ed)
    if ((evt.ctrlKey || evt.metaKey) && evt.key === 's') {
      evt.preventDefault()
      this.app.editor.saveCurrentFile()
    }
  }

  static _insertTab(evt, ed) {
    evt.preventDefault()
    const start = ed.selectionStart
    ed.setRangeText('  ', start, ed.selectionEnd)
    ed.selectionStart = start + TAB_SPACES
    ed.selectionEnd = start + TAB_SPACES
    ed.dispatchEvent(new Event('input'))
  }

  _handleInput() {
    this.updateLineNumbers()
    this.updateCursorPos()
    const cur = this.app.currentFile
    if (cur) {
      this.app.fileBuffers[cur] = this.app.els.editor.value
      this.app.dirty.add(cur)
      this.renderTabs()
      this.app.editor.debounceSave()
    }
  }

  // ── List continuation ──

  /**
   * If the cursor is on a list line, continue the prefix
   * on Enter or clear the empty item.
   */

  static _continueList(evt, ed) {
    if (ed.selectionStart !== ed.selectionEnd)
      return
    const info = EditorInput._matchListLine(ed)
    if (!info)
      return
    evt.preventDefault()
    if (info.isEmpty)
      EditorInput._clearLine(ed, info.lineStart)
    else
      EditorInput._insertContinuation(ed, info.prefix)
  }

  /** Extract the list prefix from the current line, if any. */

  static _matchListLine(ed) {
    const pos = ed.selectionStart
    const lineStart =
      ed.value.lastIndexOf('\n', pos + INDEX_NOT_FOUND) + SINGLE_ITEM
    const line = ed.value.slice(lineStart, pos)
    const match = LIST_RE.exec(line)
    if (!match)
      return null
    const [prefix] = match
    return { isEmpty: line === prefix, lineStart, prefix }
  }

  /** Remove an empty list item (bare prefix with no content). */

  static _clearLine(ed, lineStart) {
    const pos = ed.selectionStart
    ed.setRangeText('', lineStart, pos)
    ed.selectionStart = lineStart
    ed.selectionEnd = lineStart
    ed.dispatchEvent(new Event('input'))
  }

  /** Insert a newline followed by the same list prefix. */

  static _insertContinuation(ed, prefix) {
    const pos = ed.selectionStart
    const insertion = `\n${prefix}`
    ed.setRangeText(insertion, pos, ed.selectionEnd)
    ed.selectionStart = pos + insertion.length
    ed.selectionEnd = ed.selectionStart
    ed.dispatchEvent(new Event('input'))
  }

}
