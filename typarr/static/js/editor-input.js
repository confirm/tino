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

  /** @param {TyparrApp} app - Main application instance. */

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
    new ResizeObserver(() => this._scheduleLineUpdate()).observe(ed)
  }

  _scheduleLineUpdate() {
    if (this._lineUpdateRaf)
      return
    this._lineUpdateRaf = requestAnimationFrame(() => {
      this._lineUpdateRaf = null
      this.updateLineNumbers()
    })
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

  /** Recalculate line numbers in the editor gutter, accounting for wrapped lines. */

  updateLineNumbers() {
    const ed = this.app.els.editor
    if (!ed.clientWidth)
      return
    const cs = getComputedStyle(ed)
    const gutter = this.app.els.lineNumbers
    const mirror = this._getOrUpdateMirror(ed, cs)
    EditorInput._syncGutterPadding(gutter, cs)
    mirror.value = 'X'
    const baseHeight = mirror.scrollHeight
    this._buildLineSpans(gutter, ed, mirror, baseHeight)
    gutter.scrollTop = ed.scrollTop
  }

  static _syncGutterPadding(gutter, cs) {
    gutter.style.paddingTop = cs.paddingTop
    gutter.style.paddingBottom = cs.paddingBottom
  }

  _buildLineSpans(gutter, ed, mirror, baseHeight) {
    this._refreshHeightCache(ed.clientWidth)
    const lines = ed.value.split('\n')
    const fragment = document.createDocumentFragment()
    lines.forEach((line, idx) => {
      fragment.appendChild(
        this._createLineSpan(idx, line, mirror, baseHeight),
      )
    })
    gutter.innerHTML = ''
    gutter.appendChild(fragment)
  }

  _refreshHeightCache(width) {
    // Width change invalidates the cache: wrapping depends on width.
    if (this._cacheWidth !== width) {
      this._heightCache = new Map()
      this._cacheWidth = width
    }
  }

  _createLineSpan(idx, line, mirror, baseHeight) {
    const span = document.createElement('span')
    span.className = 'line-number'
    span.textContent = idx + SINGLE_ITEM
    const height = this._measureLineCached(line, mirror)
    if (height > baseHeight)
      span.style.height = `${height}px`
    return span
  }

  _measureLineCached(line, mirror) {
    if (!this._heightCache.has(line)) {
      mirror.value = line || ' '
      this._heightCache.set(line, mirror.scrollHeight)
    }
    return this._heightCache.get(line)
  }

  /** Create or update a hidden textarea mirror matching the editor's styling. */

  _getOrUpdateMirror(ed, cs) {
    const width = `${ed.clientWidth}px`
    if (this._mirror) {
      this._mirror.style.width = width
      return this._mirror
    }
    this._mirror = EditorInput._createMirror(cs, width, ed.parentNode)
    return this._mirror
  }

  static _createMirror(cs, width, container) {
    const mirror = document.createElement('textarea')
    mirror.setAttribute('aria-hidden', 'true')
    mirror.style.cssText =
      'position:absolute;visibility:hidden;height:auto;border:none;'
      + 'white-space:pre-wrap;overflow-wrap:break-word;box-sizing:border-box;'
      + `font:${cs.font};line-height:${cs.lineHeight};tab-size:${cs.tabSize};`
      + `padding:0 ${cs.paddingRight} 0 ${cs.paddingLeft};width:${width}`
    mirror.rows = SINGLE_ITEM
    container.appendChild(mirror)
    return mirror
  }

  /** Update the cursor position display. */

  updateCursorPos() {
    const val = this.app.els.editor.value
    const pos = this.app.els.editor.selectionStart
    const { col, line } = EditorInput._cursorPosition(val, pos)
    this.app.els.cursorPos.textContent = `Ln ${line}, Col ${col}`
  }

  static _cursorPosition(val, pos) {
    let line = SINGLE_ITEM
    let lastNewline = INDEX_NOT_FOUND
    for (let idx = 0; idx < pos; idx += SINGLE_ITEM) {
      if (val[idx] === '\n') {
        line += SINGLE_ITEM
        lastNewline = idx
      }
    }
    return { col: pos - lastNewline, line }
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
    if (!cur)
      return
    this.app.fileBuffers[cur] = this.app.els.editor.value

    // Only rebuild tab bar on clean -> dirty transition, not every keystroke.
    const wasClean = !this.app.dirty.has(cur)
    this.app.dirty.add(cur)
    if (wasClean)
      this.renderTabs()
    this.app.editor.debouncePreview()
    this.app.editor.debounceSave()
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
