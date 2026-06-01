import { ISO_DATETIME_LEN, escapeHtml } from './constants.js'

/**
 * Editor-adjacent UI: tab bar, file-tree highlight, cursor-position display,
 * status-bar mtime, and dirty/save bookkeeping on input.
 *
 * Tab handling, line numbers, key bindings, and list continuation moved to
 * CodeMirror; this class is the slim glue layer between CM and the rest of
 * the app.
 */

export class EditorInput {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  /** Bind editor input events. */

  bind() {
    this.app.els.editor.onChange(() => this._handleInput())
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
      '<span class="material-symbols-outlined tab-icon-dirty">edit</span>'
    const closeBtn =
      '<button class="tab-close" title="Close">&times;</button>'
    const icon = isDirty ? dirtyIcon : closeBtn
    div.innerHTML = `${icon}<span>${escapeHtml(tabPath)}</span>`
    bar.appendChild(div)
  }

  /** Highlight the active file in the tree. */

  highlightFileItem(path) {
    this.app.els.fileTree.querySelectorAll('.file-item').forEach(el => {
      el.classList.toggle('active', el.dataset.file === path)
    })
  }

  /** Update the cursor position display. */

  updateCursorPos() {
    const { col, line } = this.app.els.editor.getCursorPosition()
    this.app.els.cursorPos.textContent = `Ln ${line}, Col ${col}`
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

  _handleInput() {
    this.updateCursorPos()
    const cur = this.app.currentFile
    if (!cur)
      return
    this.app.fileBuffers[cur] = this.app.els.editor.content

    // Only rebuild tab bar on clean -> dirty transition, not every keystroke.
    const wasClean = !this.app.dirty.has(cur)
    this.app.dirty.add(cur)
    if (wasClean)
      this.renderTabs()
    this.app.editor.debounceSave()
  }

}
