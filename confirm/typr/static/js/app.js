import { EditorManager } from './editor-manager.js'
import { FileTree } from './file-tree.js'
import { GitManager } from './git-manager.js'
import { PanelResize } from './panel-resize.js'
import { PreviewManager } from './preview-manager.js'
import { TemplatePicker } from './template-picker.js'
import { Toast } from './toast.js'
import { TyprAPI } from './api.js'

/**
 * Main application controller for the Typr editor.
 * Coordinates managers for files, editor, git, and preview.
 */

class TyprApp {

  constructor() {
    this.api = new TyprAPI()
    this.dirty = new Set()
    this._resetState()
    this._buildElementRefs()
    this._initManagers()
  }

  _resetState() {
    this.bucket = null
    this.bucketRole = null
    this.currentFile = null
    this.isAdmin = false
    this.openTabs = []
    this.fileBuffers = {}
    this.fileMtimes = {}
    this.gitStatuses = {}
    this.zoom = 100
  }

  _buildElementRefs() {
    this.els = {
      binaryPreview: document.getElementById('binary-preview'),
      bucketBtn: document.getElementById('bucket-btn'),
      bucketDialogTitle: document.getElementById('bucket-dialog-title'),
      bucketFormDesc: document.getElementById('bucket-form-desc'),
      bucketFormSlug: document.getElementById('bucket-form-slug'),
      bucketLabel: document.getElementById('bucket-label'),
      bucketPicker: document.getElementById('bucket-picker'),
      bucketPickerList: document.getElementById('bucket-picker-list'),
      commitDialog: document.getElementById('commit-dialog'),
      commitFiles: document.getElementById('commit-files'),
      commitMessage: document.getElementById('commit-message'),
      cursorPos: document.getElementById('cursor-pos'),
      editor: document.getElementById('editor'),
      fileSearch: document.getElementById('file-search'),
      fileTree: document.getElementById('file-tree'),
      lineNumbers: document.getElementById('line-numbers'),
      previewPage: document.getElementById('preview-page'),
      statusBarModified: document.getElementById('status-bar-modified'),
      tabBar: document.getElementById('tab-bar'),
      userLabel: document.getElementById('user-label'),
      zoomLabel: document.getElementById('zoom-level'),
    }
  }

  _initManagers() {
    this.toast = new Toast()
    this.editor = new EditorManager(this)
    this.fileTree = new FileTree(this)
    this.git = new GitManager(this)
    this.panelResize = new PanelResize()
    this.preview = new PreviewManager(this)
    this.templatePicker = new TemplatePicker(this)
  }

  /** Initialize the app: bind events and load buckets. */

  async init() {
    this._bindAll()
    await this._loadUser()
    await this.fileTree.loadBuckets()
  }

  _bindAll() {
    this.toast.bind()
    this._bindToolbar()
    this._bindGlobalErrors()
    this.editor.bindEditor()
    this._bindFileTree()
    this.templatePicker.bind()
    this.preview.bindZoom()
    this._bindPanelResize()
  }

  _bindFileTree() {
    this.fileTree.bindTreeClicks()
    this.fileTree.bindUploadDrop()
    this.fileTree.bindBucketPicker()
    this.fileTree.bindSearch()
  }

  _bindGlobalErrors() {
    window.addEventListener('unhandledrejection', evt => {
      const msg = evt.reason && evt.reason.message
      if (msg)
        this.toast.error(msg)
    })
  }

  async _loadUser() {
    try {
      const user = await this.api.me()
      this.els.userLabel.textContent = user.username
      this.isAdmin = user.is_admin
    }
    catch {
      this.els.userLabel.textContent = 'anonymous'
      this.isAdmin = false
    }
  }

  /**
   * Switch to a different bucket: reset editor state, load git status and files.
   * @param {string} slug - Bucket identifier.
   */

  async selectBucket(slug, role) {
    if (!slug)
      return
    this.bucket = slug
    this.bucketRole = role || null
    this.editor.resetState()
    this._applyRoleVisibility()
    await this.git.loadStatus()
    await this.fileTree.loadFiles()
  }

  /** Show or hide editor actions based on the user's role in the current bucket. */

  _applyRoleVisibility() {
    const canEdit =
      this.bucketRole === 'editor' || this.bucketRole === 'committer'
    const canCommit = this.bucketRole === 'committer'
    document.getElementById('btn-new').classList.toggle('hidden', !canEdit)
    document.getElementById('btn-template').classList.toggle('hidden', !canEdit)
    document.getElementById('btn-save').classList.toggle('hidden', !canEdit)
    document.getElementById('btn-commit').classList.toggle('hidden', !canCommit)
  }

  // ── Event binding ──

  _bindToolbar() {
    this._bindBucketSelect()
    this._bindFileButtons()
    this._bindGitButtons()
    this._bindThemeToggle()
    this._bindTabBar()
    TyprApp._bindLogout()
  }

  _bindBucketSelect() {
    this.els.bucketBtn.addEventListener(
      'click',
      () => this.fileTree.openBucketPicker(),
    )
  }

  _bindFileButtons() {
    document.getElementById('btn-new')
      .addEventListener('click', () => {
        this.editor.createNewFile()
      })
    document.getElementById('btn-template')
      .addEventListener('click', () => {
        this.templatePicker.open()
      })
    document.getElementById('btn-save')
      .addEventListener('click', () => {
        this.editor.saveCurrentFile()
      })
  }

  _bindGitButtons() {
    document.getElementById('btn-commit')
      .addEventListener('click', () => {
        this.git.openDialog()
      })
    document.getElementById('btn-commit-submit')
      .addEventListener('click', () => {
        this.git.submit()
      })
    document.getElementById('btn-commit-cancel')
      .addEventListener('click', () => {
        this.git.closeDialog()
      })
    this.els.commitDialog.addEventListener('click', evt => {
      if (evt.target === this.els.commitDialog)
        this.git.closeDialog()
    })
    this._bindHistoryButtons()
  }

  _bindHistoryButtons() {
    const historyDialog = document.getElementById('history-dialog')
    document.getElementById('btn-history')
      .addEventListener('click', () => {
        this.git.openHistory(this.currentFile)
      })
    document.getElementById('btn-bucket-history')
      .addEventListener('click', () => {
        this.git.openHistory()
      })
    document.getElementById('history-search')
      .addEventListener('input', evt => {
        this.git.filterHistory(evt.target.value)
      })
    document.getElementById('btn-history-close')
      .addEventListener('click', () => {
        this.git.closeHistory()
      })
    document.getElementById('btn-history-cancel')
      .addEventListener('click', () => {
        this.git.closeHistory()
      })
    document.getElementById('btn-history-restore')
      .addEventListener('click', () => {
        this.git.restoreFromHistory()
      })
    historyDialog.addEventListener('click', evt => {
      if (evt.target === historyDialog)
        this.git.closeHistory()
    })
  }

  _bindThemeToggle() {
    this.themeTarget = document.documentElement
    const saved = localStorage.getItem('typr:theme')
    if (saved)
      this.themeTarget.setAttribute('data-theme', saved)
    document.getElementById('btn-theme')
      .addEventListener('click', () => {
        const current =
          this.themeTarget.getAttribute('data-theme')
        const next = current === 'dark' ? 'light' : 'dark'
        this.themeTarget.setAttribute('data-theme', next)
        localStorage.setItem('typr:theme', next)
      })
  }

  _bindTabBar() {
    this.els.tabBar.addEventListener('click', evt => {
      const closeBtn = evt.target.closest('.tab-close')
      if (closeBtn) {
        const tab = closeBtn.closest('.tab')
        this.editor.closeTab(tab.dataset.file)
        return
      }
      const tab = evt.target.closest('.tab')
      if (tab)
        this.editor.openFile(tab.dataset.file)
    })
  }

  static _bindLogout() {
    document.getElementById('btn-logout')
      .addEventListener('click', () => {
        window.location.href = '/logout'
      })
  }

  _bindPanelResize() {
    const fileExplorer =
      document.getElementById('file-explorer')
    const previewPanel =
      document.getElementById('preview-panel')
    this.panelResize.init(
      'resize-left', () => fileExplorer, 'left',
    )
    this.panelResize.init(
      'resize-right', () => previewPanel, 'right',
    )
  }

}

document.addEventListener('DOMContentLoaded', () => {
  const app = new TyprApp()
  app.init()
})
