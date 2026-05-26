import {
  ISO_DATETIME_LEN,
  SHA_SHORT_LEN,
  STATUS_CLASSES,
  STATUS_ICONS,
  escapeHtml,
} from './constants.js'

/**
 * Manages git operations and the commit dialog.
 */

export class GitManager {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._selectedRef = null
  }

  /** Fetch git status for all files. */

  async loadStatus() {
    if (!this.app.bucket)
      return
    const statuses = await this.app.api.gitStatus(this.app.bucket)
    this.app.gitStatuses = {}
    statuses.forEach(item => {
      this.app.gitStatuses[item.path] = item.status
    })
  }

  /** Open the commit dialog with changed file checkboxes. */

  async openDialog() {
    if (!this.app.bucket)
      return
    await this.loadStatus()
    const paths = Object.keys(this.app.gitStatuses)
    if (paths.length === 0)
      this._showEmptyDialog()
    else
      this._showFileDialog(paths)
  }

  _showFileDialog(paths) {
    this.app.els.commitFiles.innerHTML = ''
    this._renderFileList(this.app.els.commitFiles, paths)
    this.app.els.commitMessage.value = ''
    this.app.els.commitDialog.classList.add('visible')
    this.app.els.commitMessage.focus()
  }

  _showEmptyDialog() {
    this.app.els.commitFiles.innerHTML =
      '<li class="commit-empty">No changes to commit</li>'
    this.app.els.commitMessage.value = ''
    this.app.els.commitDialog.classList.add('visible')
  }

  _renderFileList(list, paths) {
    paths.forEach(filePath => {
      const li = document.createElement('li')
      li.className = 'commit-file-item'
      const status = this.app.gitStatuses[filePath]
      const safe = escapeHtml(filePath)
      li.innerHTML =
        '<label>' +
        `<input type="checkbox" value="${safe}" checked> ` +
        `<span class="material-symbols-outlined git-badge ${STATUS_CLASSES[status]}">` +
        `${STATUS_ICONS[status]}</span> ${safe}</label>`
      list.appendChild(li)
    })
  }

  /** Hide the commit dialog overlay. */

  closeDialog() {
    this.app.els.commitDialog.classList.remove('visible')
  }

  /** Validate and submit a git commit. */

  async submit() {
    const files = this._collectCheckedFiles()
    const message = this.app.els.commitMessage.value.trim()
    if (!message) {
      this.app.toast.error('Please enter a commit message.')
      return
    }
    if (files.length === 0) {
      this.app.toast.error('Please select at least one file.')
      return
    }
    await this._executeCommit(files, message)
  }

  _collectCheckedFiles() {
    const checked = this.app.els.commitFiles
      .querySelectorAll('input[type="checkbox"]:checked')
    return Array.from(checked, cb => cb.value)
  }

  async _executeCommit(files, message) {
    try {
      await this.app.api.gitCommit(this.app.bucket, files, message)
      this.closeDialog()
      await this.loadStatus()
      await this.app.fileTree.loadFiles()
    }
    catch (err) {
      this.app.toast.error(`Commit failed: ${err.message}`)
    }
  }

  // ── History ──

  /** Open the history dialog, optionally filtered to a single file. */

  async openHistory(filePath) {
    if (!this.app.bucket)
      return
    this._historyFile = filePath || null
    this._selectedRef = null
    this._selectedPath = null
    this._allCommits = []
    GitManager._resetHistoryUi(filePath)
    await this._loadHistoryCommits(filePath)
    document.getElementById('history-dialog').classList.add('visible')
  }

  static _resetHistoryUi(filePath) {
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

  async _loadHistoryCommits(filePath) {
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

  filterHistory(query) {
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
      const data = await this.app.api.gitShow(this.app.bucket, sha, path)
      preview.innerHTML =
        `<pre class="history-content">${escapeHtml(data.content)}</pre>`
      restoreBtn.disabled = false
    }
    catch {
      preview.innerHTML =
        '<p class="preview-empty">Could not load file at this commit.</p>'
      restoreBtn.disabled = true
    }
  }

  /** Restore the selected file from the chosen commit into the working tree. */

  async restoreFromHistory() {
    const path = this._selectedPath || this._historyFile
    if (!this._selectedRef || !path)
      return
    try {
      await this.app.api.gitRestore(this.app.bucket, this._selectedRef, [path])
      this.closeHistory()
      this._clearFileCache(path)
      await this.loadStatus()
      await this.app.fileTree.loadFiles()
      await this.app.editor.openFile(path)
    }
    catch (err) {
      this.app.toast.error(`Restore failed: ${err.message}`)
    }
  }

  _clearFileCache(path) {
    delete this.app.fileBuffers[path]
    this.app.dirty.delete(path)
  }

  /** Close the history dialog and reset selection state. */

  closeHistory() {
    document.getElementById('history-dialog').classList.remove('visible')
    this._selectedRef = null
    this._selectedPath = null
  }

}
