import {
  DEBOUNCE_MS,
  INDEX_NOT_FOUND,
  SINGLE_ITEM,
  escapeHtml,
} from './constants.js'
import { CollabSession } from './collab.js'
import { EditorInput } from './editor-input.js'
import { EditorToolbar } from './editor-toolbar.js'

const PLACEHOLDER = 'Select a file to start editing...'

/**
 * Manages file loading, saving, tabs, and binary preview.
 * Delegates low-level textarea interactions to EditorInput.
 */

export class EditorManager {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this.input = new EditorInput(app)
    this.toolbar = new EditorToolbar(app)
    this.collab = null
    this._saveTimer = null
  }

  /** Open a file in the editor, loading from cache or API. */

  async openFile(path) {
    if (!this.app.bucket)
      return
    this._saveCurrentBuffer()
    await this._loadContent(path)
    this.app.currentFile = path
    this.app.els.editor.placeholder = ''
    if (this.app.openTabs.indexOf(path) === INDEX_NOT_FOUND)
      this.app.openTabs.push(path)
    this._refreshEditorUi()
    this._connectCollab(path)
    await this.app.preview.update()
  }

  _saveCurrentBuffer() {
    const cur = this.app.currentFile
    if (cur && this.app.dirty.has(cur))
      this.app.fileBuffers[cur] = this.app.els.editor.value
  }

  async _loadContent(path) {
    if (path in this.app.fileBuffers) {
      this._showTextEditor(this.app.fileBuffers[path])
      return
    }
    const data = await this.app.api.readFile(
      this.app.bucket, path,
    )
    if (data.binary) {
      this._showBinaryPreview(path)
      return
    }
    this.app.fileBuffers[path] = data.content
    this.app.fileMtimes[path] = data.modified
    this._showTextEditor(data.content)
  }

  _showTextEditor(content) {
    this.app.els.binaryPreview.classList.add('hidden')
    this.app.els.binaryPreview.innerHTML = ''
    this.app.els.editor.value = content
    this.app.els.editor.readOnly = false
    this.app.els.editor.classList.remove('hidden')
    this.app.els.lineNumbers.classList.remove('hidden')
    this._showToolbarIfEditable()
  }

  _showToolbarIfEditable() {
    const role = this.app.bucketRole
    if (role === 'editor' || role === 'committer')
      this.toolbar.show()
    else
      this.toolbar.hide()
  }

  _showBinaryPreview(path) {
    this.toolbar.hide()
    this.app.els.editor.classList.add('hidden')
    this.app.els.lineNumbers.classList.add('hidden')
    const bp = this.app.els.binaryPreview
    const rawUrl = this._rawFileUrl(path)
    const name = path.split('/').pop()
    bp.innerHTML = EditorManager._binaryHtml(path, rawUrl, name)
    bp.classList.remove('hidden')
  }

  static _binaryHtml(path, rawUrl, name) {
    const dl = `<a class="btn-download" href="${rawUrl}" download="${escapeHtml(name)}">` +
      '<span class="material-symbols-outlined">download</span>' +
      `Download ${escapeHtml(name)}</a>`
    if (EditorManager._isImage(path))
      return `<img src="${rawUrl}" alt="${escapeHtml(path)}">${dl}`
    return `<p>Binary file — cannot be edited here.</p>${dl}`
  }

  _rawFileUrl(path) {
    const slug = encodeURIComponent(this.app.bucket)
    return `/api/buckets/${slug}/files/raw/${path}`
  }

  static _isImage(path) {
    const ext = path.split('.').pop().toLowerCase()
    return ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)
  }

  _refreshEditorUi() {
    this.input.renderTabs()
    this.input.highlightFileItem(this.app.currentFile)
    this.input.updateLineNumbers()
    this.input.updateCursorPos()
    this.input.updateStatusBar()
    this.app.els.editor.focus()
  }

  /** Save the current file to the backend. */

  async saveCurrentFile() {
    if (!this.app.bucket || !this.app.currentFile)
      return
    const content = this.app.els.editor.value
    const result = await this.app.api.saveFile(
      this.app.bucket, this.app.currentFile, content,
    )
    this.app.fileBuffers[this.app.currentFile] = content
    this.app.fileMtimes[this.app.currentFile] = result.modified
    this.app.dirty.delete(this.app.currentFile)
    await this._refreshAfterSave()
  }

  async _refreshAfterSave() {
    this.input.renderTabs()
    this.input.updateStatusBar()
    await this.app.git.loadStatus()
    await this.app.fileTree.loadFiles()
    await this.app.preview.update()
  }

  /** Prompt for a filename and create a new file. */

  async createNewFile() {
    // eslint-disable-next-line no-alert
    const name = prompt('File name:')
    if (!name || !this.app.bucket)
      return
    try {
      await this.app.api.createFile(this.app.bucket, name, '')
      await this.app.git.loadStatus()
      await this.app.fileTree.loadFiles()
      await this.openFile(name)
    }
    catch (err) {
      this.app.toast.error(
        `Could not create file: ${err.message}`,
      )
    }
  }

  /** Close a tab and switch to an adjacent one if needed. */

  closeTab(path) {
    const idx = this.app.openTabs.indexOf(path)
    if (idx === INDEX_NOT_FOUND)
      return
    this.app.openTabs.splice(idx, SINGLE_ITEM)
    delete this.app.fileBuffers[path]
    this.app.dirty.delete(path)
    if (this.app.currentFile === path) {
      this._disconnectCollab()
      this._switchAfterClose(idx)
    }
    this.input.renderTabs()
  }

  _switchAfterClose(idx) {
    if (this.app.openTabs.length > 0) {
      const next =
        this.app.openTabs[Math.max(0, idx - SINGLE_ITEM)]
      this.openFile(next)
      return
    }
    this._disconnectCollab()
    this.app.currentFile = null
    this._showTextEditor('')
    this.app.els.editor.placeholder = PLACEHOLDER
    this.input.updateLineNumbers()
    this.input.updateStatusBar()
  }

  /** Close tabs for files that no longer exist on disk. */

  reconcileTabs(existingPaths) {
    const stale = this.app.openTabs.filter(
      tp => !existingPaths.has(tp),
    )
    if (!stale.length)
      return
    stale.forEach(tp => {
      const idx = this.app.openTabs.indexOf(tp)
      if (idx !== INDEX_NOT_FOUND)
        this.app.openTabs.splice(idx, SINGLE_ITEM)
      delete this.app.fileBuffers[tp]
      this.app.dirty.delete(tp)
    })
    if (this.app.openTabs.includes(this.app.currentFile))
      this.input.renderTabs()
    else
      this._switchAfterClose(0)
  }

  /** Schedule an auto-save after typing stops. */

  debounceSave() {
    clearTimeout(this._saveTimer)
    this._saveTimer = setTimeout(
      () => this.saveCurrentFile(),
      DEBOUNCE_MS,
    )
  }

  /** Reset editor state when switching buckets. */

  resetState() {
    this._disconnectCollab()
    this.toolbar.hide()
    this._clearOpenState()
    this._showTextEditor('')
    this.app.els.editor.placeholder = PLACEHOLDER
    this.app.els.tabBar.innerHTML = ''
    this.input.updateLineNumbers()
  }

  _clearOpenState() {
    this.app.openTabs = []
    this.app.currentFile = null
    this.app.fileBuffers = {}
    this.app.fileMtimes = {}
    this.app.dirty.clear()
  }

  /** Bind editor events (delegates to EditorInput). */

  bindEditor() {
    this.input.bind()
    this.toolbar.bind()
  }

  // ── Collab ──

  _connectCollab(path) {
    this._disconnectCollab()
    const role = this.app.bucketRole
    const canEdit = role === 'editor' || role === 'committer'
    const isText = !this.app.els.editor.classList.contains('hidden')
    if (!path || !canEdit || !isText)
      return
    this.collab = new CollabSession(
      this.app.bucket,
      path,
      this.app.els.editor,
      st => this._onCollabStatus(st),
    )
    this.collab.connect()
  }

  _disconnectCollab() {
    if (this.collab) {
      this.collab.disconnect()
      this.collab = null
    }
  }

  _onCollabStatus(status) {
    if (status === 'disconnected')
      this.app.toast.error('Collaboration disconnected')
    else if (status === 'reconnected')
      this.app.toast.success('Collaboration reconnected')
  }

}
