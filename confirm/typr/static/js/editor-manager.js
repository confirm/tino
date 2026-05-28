import {
  DEBOUNCE_MS,
  INDEX_NOT_FOUND,
  SINGLE_ITEM,
} from './constants.js'
import { loadSavedTabs, persistTabs } from './tab-store.js'
import { BinaryPreview } from './editor-binary.js'
import { EditorCollab } from './editor-collab.js'
import { EditorHighlight } from './editor-highlight.js'
import { EditorInput } from './editor-input.js'
import { EditorToolbar } from './editor-toolbar.js'
import { writeRoute } from './router.js'

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
    this.binary = new BinaryPreview(app, this.toolbar)
    this.collab = new EditorCollab(app)
    this.highlight = new EditorHighlight(
      app.els.editor, app.els.editorHighlight,
    )
    this._saveTimer = null
  }

  /** Open a file in the editor, loading from cache or API. */

  async openFile(path) {
    if (!this.app.bucket)
      return
    this._flushPendingSave()

    /*
     * Generation counter: a slow _loadContent must not overwrite a newer
     * tab switch. If the user clicks B while A is still loading, A's
     * post-load UI updates are dropped when gen no longer matches.
     */

    this._openGeneration =
      (this._openGeneration || 0) + SINGLE_ITEM
    const gen = this._openGeneration
    await this._loadContent(path)
    if (gen !== this._openGeneration)
      return
    this._activateTab(path)
    await this.app.preview.update()
  }

  _flushPendingSave() {
    if (this._saveTimer) {
      clearTimeout(this._saveTimer)
      this._saveTimer = null
      this.saveCurrentFile()
    }
  }

  _activateTab(path) {
    this.app.currentFile = path
    this.app.els.editor.placeholder = ''
    if (this.app.openTabs.indexOf(path) === INDEX_NOT_FOUND)
      this.app.openTabs.push(path)
    this._refreshEditorUi()
    this.collab.connect(path)
    this._persistOpenState(path)
  }

  async _loadContent(path) {
    if (path in this.app.fileBuffers) {
      this._showTextEditor(this.app.fileBuffers[path])
      return
    }
    const data = await this.app.api.readFile(
      this.app.bucket, path,
    )
    if (data.binary || BinaryPreview.isImage(path)) {
      this.binary.show(path)
      return
    }
    this.app.fileBuffers[path] = data.content
    this.app.fileMtimes[path] = data.modified
    this._showTextEditor(data.content)
  }

  _showTextEditor(content) {
    this.app.els.binaryPreview.classList.add('hidden')
    this.app.els.binaryPreview.innerHTML = ''
    const role = this.app.bucketRole
    const canEdit = role === 'editor' || role === 'committer'
    this.app.els.editor.value = content
    this.app.els.editor.disabled = !canEdit
    this.app.els.editor.classList.remove('hidden')
    this.app.els.lineNumbers.classList.remove('hidden')
    if (canEdit)
      this.toolbar.show()
    else
      this.toolbar.hide()
  }

  _refreshEditorUi() {
    this.input.renderTabs()
    this.input.highlightFileItem(this.app.currentFile)
    this.input.updateLineNumbers()
    this.input.updateCursorPos()
    this.input.updateStatusBar()
    this.highlight.sync()
    this.app.els.editor.focus()
  }

  /** Save the current file to the backend. */

  async saveCurrentFile() {
    const path = this.app.currentFile
    if (!this.app.bucket || !path || BinaryPreview.isImage(path))
      return
    if (!(path in this.app.fileBuffers))
      return
    const content = this.app.fileBuffers[path]
    const result = await this.app.api.saveFile(
      this.app.bucket, path, content,
    )
    this.app.fileMtimes[path] = result.modified
    this.app.dirty.delete(path)
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
      this.collab.disconnect()
      this._switchAfterClose(idx)
    }
    this.input.renderTabs()
    this.saveTabs()
  }

  _switchAfterClose(idx) {
    if (this.app.openTabs.length > 0) {
      const next =
        this.app.openTabs[Math.max(0, idx - SINGLE_ITEM)]
      this.openFile(next)
      return
    }
    this._clearEditor()
  }

  _clearEditor() {
    this.collab.disconnect()
    this.app.currentFile = null
    this._showTextEditor('')
    this.app.els.editor.disabled = true
    this.app.els.editor.placeholder = PLACEHOLDER
    this.input.updateLineNumbers()
    this.input.updateStatusBar()
    writeRoute(this.app.bucket, null)
  }

  /** Persist open tabs to localStorage for the current bucket. */

  saveTabs() {
    if (this.app.bucket)
      persistTabs(this.app.bucket, this.app.openTabs)
  }

  /** Restore saved tabs from localStorage, filtering stale paths. */

  restoreTabs() {
    if (!this.app.bucket)
      return
    const valid = loadSavedTabs(
      this.app.bucket, this.app.fileTree.filePaths,
    )
    if (valid.length > 0) {
      this.app.openTabs = valid
      this.input.renderTabs()
    }
  }

  _persistOpenState(path) {
    writeRoute(this.app.bucket, path)
    this.saveTabs()
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
    this.saveTabs()
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
    this.collab.disconnect()
    this.toolbar.hide()
    this._clearOpenState()
    this._showTextEditor('')
    this.app.els.editor.disabled = true
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

}
