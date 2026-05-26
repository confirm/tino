import {
  ISO_DATETIME_LEN,
  SHA_SHORT_LEN,
  escapeHtml,
} from './constants.js'
import { BinaryPreview } from './editor-binary.js'

/**
 * Manages the git history dialog: browsing commits,
 * viewing file content at a specific ref, and restoring files.
 */

export class GitHistory {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._selectedRef = null
  }

  /** Bind history dialog event listeners. */

  bind() {
    this._bindButtons()
    this._bindDialog()
  }

  _bindButtons() {
    document.getElementById('btn-history')
      .addEventListener('click', () => {
        this.open(this.app.currentFile)
      })
    document.getElementById('btn-bucket-history')
      .addEventListener('click', () => {
        this.open()
      })
    document.getElementById('history-search')
      .addEventListener('input', evt => {
        this.filter(evt.target.value)
      })
    document.getElementById('btn-history-restore')
      .addEventListener('click', () => {
        this.restore()
      })
  }

  _bindDialog() {
    const dialog = document.getElementById('history-dialog')
    document.getElementById('btn-history-close')
      .addEventListener('click', () => {
        this.close()
      })
    document.getElementById('btn-history-cancel')
      .addEventListener('click', () => {
        this.close()
      })
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
    GitHistory._resetUi(filePath)
    await this._loadCommits(filePath)
    document.getElementById('history-dialog').classList.add('visible')
  }

  static _resetUi(filePath) {
    const title = document.getElementById('history-title')
    const search = document.getElementById('history-search')
    title.textContent = filePath ? `History — ${filePath}` : 'Bucket History'
    search.value = ''
    document.getElementById('history-list').innerHTML = ''
    document.getElementById('history-files').innerHTML = ''
    document.getElementById('history-preview').innerHTML =
      '<p class="preview-empty">Select a commit to browse files.</p>'
    document.getElementById('btn-history-restore').disabled = true
  }

  async _loadCommits(filePath) {
    try {
      this._allCommits = await this.app.api.gitLog(
        this.app.bucket, filePath || null,
      )
      this._renderCommitList(this._allCommits)
    }
    catch {
      document.getElementById('history-list').innerHTML =
        '<li class="history-empty">Could not load history.</li>'
    }
  }

  /** Filter the commit list by message, author, or SHA prefix. */

  filter(query) {
    const lowerQuery = query.toLowerCase()
    const filtered = lowerQuery ? this._filterCommits(lowerQuery) : this._allCommits
    this._renderCommitList(filtered)
  }

  _filterCommits(lowerQuery) {
    return this._allCommits.filter(commit =>
      commit.message.toLowerCase().includes(lowerQuery) ||
        commit.author.toLowerCase().includes(lowerQuery) ||
        commit.sha.startsWith(lowerQuery),
    )
  }

  _renderCommitList(commits) {
    const list = document.getElementById('history-list')
    list.innerHTML = ''
    if (commits.length === 0) {
      list.innerHTML = '<li class="history-empty">No commits found.</li>'
      return
    }
    commits.forEach(commit => {
      const li = document.createElement('li')
      li.className = 'history-item'
      li.dataset.sha = commit.sha
      const date = new Date(commit.timestamp)
      const ts = date.toISOString().slice(0, ISO_DATETIME_LEN).replace('T', ' ')
      li.innerHTML =
        `<span class="history-message">${escapeHtml(commit.message)}</span>` +
        `<span class="history-meta"><span>${commit.author}</span>` +
        `<span>${ts}</span>` +
        `<span class="history-sha">${commit.sha.substring(0, SHA_SHORT_LEN)}</span></span>`
      li.addEventListener('click', () => this._selectCommit(commit.sha, li))
      list.appendChild(li)
    })
  }

  async _selectCommit(sha, li) {
    document.getElementById('history-list')
      .querySelectorAll('.history-item').forEach(el => el.classList.remove('active'))
    li.classList.add('active')
    Object.assign(this, { _selectedPath: null, _selectedRef: sha })
    document.getElementById('btn-history-restore').disabled = true
    if (this._historyFile) {
      document.getElementById('history-files').innerHTML = ''
      await this._showFileContent(sha, this._historyFile)
      return
    }
    await this._renderFileTree(sha)
  }

  async _renderFileTree(sha) {
    const files = document.getElementById('history-files')
    const preview = document.getElementById('history-preview')
    try {
      const tree = await this.app.api.gitTree(this.app.bucket, sha)
      files.innerHTML = ''
      tree.forEach(path => {
        const fli = document.createElement('li')
        fli.className = 'history-file-item'
        fli.dataset.path = path
        fli.innerHTML =
          '<span class="material-symbols-outlined">description</span>' +
          `<span>${escapeHtml(path)}</span>`
        fli.addEventListener('click', () => this._selectFile(sha, path, fli))
        files.appendChild(fli)
      })
      preview.innerHTML =
        '<p class="preview-empty">Select a file to view its content.</p>'
    }
    catch {
      files.innerHTML = ''
      preview.innerHTML =
        '<p class="preview-empty">Could not load file tree.</p>'
    }
  }

  async _selectFile(sha, path, li) {
    document.getElementById('history-files')
      .querySelectorAll('.history-file-item')
      .forEach(el => el.classList.remove('active'))
    li.classList.add('active')
    this._selectedPath = path
    await this._showFileContent(sha, path)
  }

  async _showFileContent(sha, path) {
    const preview = document.getElementById('history-preview')
    const restoreBtn = document.getElementById('btn-history-restore')
    try {
      if (BinaryPreview.isImage(path))
        preview.innerHTML = this._imagePreviewHtml(sha, path)
      else
        await this._showTextPreview(preview, sha, path)
      restoreBtn.disabled = false
    }
    catch {
      preview.innerHTML =
        '<p class="preview-empty">Could not load file at this commit.</p>'
      restoreBtn.disabled = true
    }
  }

  async _showTextPreview(preview, sha, path) {
    const data = await this.app.api.gitShow(this.app.bucket, sha, path)
    if (data.binary)
      preview.innerHTML = '<p class="preview-empty">Binary file</p>'
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
      await this.app.api.gitRestore(
        this.app.bucket, this._selectedRef, [path],
      )
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
