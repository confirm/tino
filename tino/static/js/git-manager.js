import {
  STATUS_CLASSES,
  STATUS_ICONS,
  escapeHtml,
} from './constants.js'
import { GitHistory } from './git-history.js'
import { renderDiffEntries } from './diff-render.js'

/**
 * Manages git operations: status, commit dialog, and history.
 * Delegates history browsing to GitHistory.
 */

export class GitManager {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this.history = new GitHistory(app)
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
    GitManager._resetDiffPane()
    this.app.els.commitMessage.value = ''
    this.app.els.commitDialog.classList.add('visible')
    this.app.els.commitMessage.focus()
  }

  _showEmptyDialog() {
    this.app.els.commitFiles.innerHTML =
      '<li class="commit-empty">No changes to commit</li>'
    GitManager._resetDiffPane()
    this.app.els.commitMessage.value = ''
    this.app.els.commitDialog.classList.add('visible')
  }

  static _resetDiffPane() {
    const pane = document.getElementById('commit-diff')
    if (pane)
      pane.innerHTML = '<p class="preview-empty">Select a file to view its diff.</p>'
  }

  _renderFileList(list, paths) {
    paths.forEach(filePath => {
      const li = document.createElement('li')
      li.className = 'commit-file-item'
      li.dataset.file = filePath
      const status = this.app.gitStatuses[filePath]
      const safe = escapeHtml(filePath)
      li.innerHTML =
        `<label><input type='checkbox' value='${safe}' checked></label>`
        + '<span class="commit-file-name">'
        + `<span class="material-symbols-outlined git-badge ${STATUS_CLASSES[status]}">`
        + `${STATUS_ICONS[status]}</span>${safe}</span>`
      list.appendChild(li)
    })
  }

  /** Load and render the diff for a single file in the preview pane. */

  async showDiffFor(filePath) {
    this._highlightFileRow(filePath)
    const pane = document.getElementById('commit-diff')
    pane.innerHTML = '<p class="preview-empty">Loading diff…</p>'
    try {
      const entries = await this.app.api.gitDiff(this.app.bucket, filePath)
      pane.innerHTML = renderDiffEntries(entries)
    }
    catch (err) {
      pane.innerHTML =
        `<p class="preview-empty">Could not load diff: ${escapeHtml(err.message)}</p>`
    }
  }

  _highlightFileRow(filePath) {
    this.app.els.commitFiles.querySelectorAll('.commit-file-item')
      .forEach(li => li.classList.toggle('active', li.dataset.file === filePath))
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

}
