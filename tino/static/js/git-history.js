import {
  ISO_DATETIME_LEN,
  SHA_SHORT_LEN,
  escapeHtml,
} from './constants.js'
import { BinaryPreview } from './editor-binary.js'
import { renderDiffEntries } from './diff-render.js'

/**
 * Manages the git history dialog: browsing commits,
 * viewing file content or diffs at a specific ref, and restoring files.
 */

export class GitHistory {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._selectedRef = null
    this._mode = 'content'
  }

  /** Bind history dialog event listeners. */

  bind() {
    this._bindButtons()
    this._bindDialog()
    this._bindLists()
  }

  _bindLists() {
    document.getElementById('history-list').addEventListener('click', evt => {
      const li = evt.target.closest('.history-item')
      if (!li)
        return
      const commit = this._allCommits.find(cm => cm.sha === li.dataset.sha)
      if (commit)
        this._selectCommit(commit, li)
    })
    document.getElementById('history-files').addEventListener('click', evt => {
      const li = evt.target.closest('.history-file-item')
      if (li && this._selectedRef)
        this._selectFile(this._selectedRef, li.dataset.path, li)
    })
  }

  _bindButtons() {
    document.getElementById('btn-history')
      .addEventListener('click', () => this.open(this.app.currentFile))
    document.getElementById('btn-bucket-history').addEventListener('click', () => this.open())
    document.getElementById('history-search')
      .addEventListener('input', evt => this.filter(evt.target.value))
    document.getElementById('btn-history-restore').addEventListener('click', () => this.restore())
    document.getElementById('history-preview-toolbar').addEventListener('click', evt => {
      const btn = evt.target.closest('.preview-toggle')
      if (btn)
        this._setMode(btn.dataset.mode)
    })
  }

  _bindDialog() {
    const dialog = document.getElementById('history-dialog')
    document.getElementById('btn-history-close').addEventListener('click', () => this.close())
    document.getElementById('btn-history-cancel').addEventListener('click', () => this.close())
    dialog.addEventListener('click', evt => {
      if (evt.target === dialog)
        this.close()
    })
  }

  /** Open the history dialog, optionally filtered to a single file. */

  async open(filePath) {
    if (!this.app.bucket)
      return
    this._historyFile = filePath || null
    this._selectedRef = null
    this._selectedPath = null
    this._allCommits = []
    this._mode = filePath ? 'diff' : 'content'
    GitHistory._resetUi(filePath)
    this._renderModeButtons()
    await this._loadCommits(filePath)
    document.getElementById('history-dialog').classList.add('visible')
  }

  static _resetUi(filePath) {
    document.getElementById('history-title').textContent =
      filePath ? `History — ${filePath}` : 'Bucket History'
    document.getElementById('history-search').value = ''
    document.getElementById('history-list').innerHTML = ''
    document.getElementById('history-files').innerHTML = ''
    document.getElementById('history-preview').innerHTML =
      '<p class="preview-empty">Select a commit to browse files.</p>'
    document.getElementById('history-preview-toolbar').classList.add('hidden')
    document.getElementById('btn-history-restore').disabled = true
  }

  _renderModeButtons() {
    document.getElementById('btn-history-mode-content')
      .classList.toggle('active', this._mode === 'content')
    document.getElementById('btn-history-mode-diff')
      .classList.toggle('active', this._mode === 'diff')
  }

  async _setMode(mode) {
    if (mode === this._mode)
      return
    this._mode = mode
    this._renderModeButtons()
    const path = this._selectedPath || this._historyFile
    if (this._selectedRef && path)
      await this._renderPreviewFor(this._selectedRef, path)
  }

  async _loadCommits(filePath) {
    try {
      this._allCommits = await this.app.api.gitLog(this.app.bucket, filePath || null)
      GitHistory._renderCommitList(this._allCommits)
    }
    catch {
      document.getElementById('history-list').innerHTML =
        '<li class="history-empty">Could not load history.</li>'
    }
  }

  /** Filter the commit list by message, author, or SHA prefix. */

  filter(query) {
    const lower = query.toLowerCase()
    const match = commit => commit.message.toLowerCase().includes(lower)
      || commit.author.toLowerCase().includes(lower)
      || commit.sha.startsWith(lower)
    GitHistory._renderCommitList(lower ? this._allCommits.filter(match) : this._allCommits)
  }

  static _renderCommitList(commits) {
    const list = document.getElementById('history-list')
    if (commits.length === 0) {
      list.innerHTML = '<li class="history-empty">No commits found.</li>'
      return
    }
    list.innerHTML = commits.map(GitHistory._commitItemHtml).join('')
  }

  static _commitItemHtml(commit) {
    const ts = new Date(commit.timestamp).toISOString()
      .slice(0, ISO_DATETIME_LEN).replace('T', ' ')
    const cls = commit.deleted ? 'history-item history-deleted' : 'history-item'
    return `<li class="${cls}" data-sha="${commit.sha}">`
      + `<span class="history-message">${escapeHtml(commit.message)}</span>`
      + `<span class="history-meta"><span>${commit.author}</span><span>${ts}</span>`
      + `<span class="history-sha">${commit.sha.substring(0, SHA_SHORT_LEN)}</span></span></li>`
  }

  async _selectCommit(commit, li) {
    document.getElementById('history-list')
      .querySelectorAll('.history-item').forEach(el => el.classList.remove('active'))
    li.classList.add('active')
    Object.assign(this, { _selectedPath: null, _selectedRef: commit.sha })
    document.getElementById('btn-history-restore').disabled = true
    if (this._historyFile)
      await this._loadFileAtCommit(commit)
    else
      await this._loadBucketAtCommit(commit.sha)
  }

  async _loadFileAtCommit(commit) {
    document.getElementById('history-files').innerHTML = ''
    document.getElementById('history-preview-toolbar').classList.remove('hidden')
    if (commit.deleted)
      GitHistory._showDeleted()
    else
      await this._renderPreviewFor(commit.sha, this._historyFile)
  }

  async _loadBucketAtCommit(sha) {
    document.getElementById('history-preview-toolbar').classList.add('hidden')
    await this._renderFileTree(sha)
  }

  static _showDeleted() {
    document.getElementById('history-preview').innerHTML =
      '<p class="preview-empty">File deleted in this commit.</p>'
    document.getElementById('btn-history-restore').disabled = true
  }

  async _renderFileTree(sha) {
    const files = document.getElementById('history-files')
    const preview = document.getElementById('history-preview')
    try {
      const tree = await this.app.api.gitChanged(this.app.bucket, sha)
      files.innerHTML = tree.map(path =>
        `<li class="history-file-item" data-path="${escapeHtml(path)}">`
          + '<span class="material-symbols-outlined">description</span>'
          + `<span>${escapeHtml(path)}</span></li>`).join('')
      preview.innerHTML = '<p class="preview-empty">Select a file to view its content.</p>'
    }
    catch {
      files.innerHTML = ''
      preview.innerHTML = '<p class="preview-empty">Could not load file tree.</p>'
    }
  }

  async _selectFile(sha, path, li) {
    document.getElementById('history-files')
      .querySelectorAll('.history-file-item')
      .forEach(el => el.classList.remove('active'))
    li.classList.add('active')
    this._selectedPath = path
    document.getElementById('history-preview-toolbar').classList.remove('hidden')
    await this._renderPreviewFor(sha, path)
  }

  async _renderPreviewFor(sha, path) {
    if (this._mode === 'diff')
      await this._showFileDiff(sha, path)
    else
      await this._showFileContent(sha, path)
  }

  async _showFileContent(sha, path) {
    const preview = document.getElementById('history-preview')
    const restoreBtn = document.getElementById('btn-history-restore')
    try {
      const data = await this.app.api.gitShow(this.app.bucket, sha, path)
      this._renderPreview(preview, data, sha, path)
      restoreBtn.disabled = Boolean(data.deleted)
    }
    catch {
      preview.innerHTML = '<p class="preview-empty">Could not load file at this commit.</p>'
      restoreBtn.disabled = true
    }
  }

  async _showFileDiff(sha, path) {
    const preview = document.getElementById('history-preview')
    const restoreBtn = document.getElementById('btn-history-restore')
    preview.innerHTML = '<p class="preview-empty">Loading diff…</p>'
    try {
      const entries = await this.app.api.gitDiff(this.app.bucket, path, sha)
      preview.innerHTML = renderDiffEntries(entries)
      restoreBtn.disabled = false
    }
    catch {
      preview.innerHTML = '<p class="preview-empty">Could not load diff.</p>'
      restoreBtn.disabled = true
    }
  }

  _renderPreview(preview, data, sha, path) {
    if (data.deleted)
      preview.innerHTML = '<p class="preview-empty">File deleted in this commit.</p>'
    else if (data.binary || BinaryPreview.isImage(path))
      preview.innerHTML = this._imagePreviewHtml(sha, path)
    else
      preview.innerHTML = `<pre class="history-content">${escapeHtml(data.content)}</pre>`
  }

  _imagePreviewHtml(sha, path) {
    const slug = encodeURIComponent(this.app.bucket)
    const ref = encodeURIComponent(sha)
    const url = `/api/buckets/${slug}/git/show/${ref}/raw/${path}`
    return `<img class="history-image" src="${url}" alt="${escapeHtml(path)}">`
  }

  /** Restore the selected file from the chosen commit. */

  async restore() {
    const path = this._selectedPath || this._historyFile
    if (!this._selectedRef || !path)
      return
    try {
      await this.app.api.gitRestore(this.app.bucket, this._selectedRef, [path])
      await this._applyRestore(path)
    }
    catch (err) {
      this.app.toast.error(`Restore failed: ${err.message}`)
    }
  }

  async _applyRestore(path) {
    this.close()
    delete this.app.fileBuffers[path]
    this.app.dirty.delete(path)
    await this.app.git.loadStatus()
    await this.app.fileTree.loadFiles()
    await this.app.editor.openFile(path)
  }

  /** Close the history dialog and reset selection state. */

  close() {
    document.getElementById('history-dialog').classList.remove('visible')
    this._selectedRef = null
    this._selectedPath = null
  }

}
