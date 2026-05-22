import {
  FILE_ICON,
  FOLDER_ICON,
  SINGLE_ITEM,
  STATUS_CLASSES,
  STATUS_ICONS,
  TOGGLE_ICON,
  escapeHtml,
} from './constants.js'
import { BucketPicker } from './bucket-picker.js'
import { TreeActions } from './tree-actions.js'
import { TreeBuilder } from './tree-builder.js'

/**
 * Manages the file explorer tree and bucket loading.
 */

export class FileTree {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this.actions = new TreeActions(app)
    this.bucketPicker = new BucketPicker(app)
  }

  /** Fetch all buckets and auto-select if only one. */

  async loadBuckets() {
    this._buckets = await this.app.api.listBuckets()
    if (this.app.bucket) {
      this.app.els.bucketLabel.textContent =
        this.app.bucket
    }
    else {
      this.app.els.bucketLabel.textContent =
        'Select bucket...'
    }

    if (this._buckets.length === SINGLE_ITEM) {
      const [only] = this._buckets
      this.app.els.bucketLabel.textContent = only.slug
      await this.app.selectBucket(only.slug, only.role)
    }
  }

  /** Open the bucket picker dialog. */

  openBucketPicker() {
    this.bucketPicker.open()
  }

  /** Bind bucket picker events. */

  bindBucketPicker() {
    this.bucketPicker.bind()
  }

  /** Fetch file list and render the hierarchical tree. */

  async loadFiles() {
    const collapsed = this._getCollapsedPaths()
    const files = await this.app.api.listFiles(this.app.bucket)
    const nodes = TreeBuilder.build(
      files, this.app.gitStatuses, this._canEdit(),
    )
    const tree = this.app.els.fileTree
    tree.innerHTML = ''
    this._renderNodes(tree, nodes, collapsed)
  }

  _getCollapsedPaths() {
    const paths = new Set()
    this.app.els.fileTree
      .querySelectorAll('.folder-item.collapsed')
      .forEach(el => paths.add(el.dataset.folder))
    return paths
  }

  _renderNodes(parent, nodes, collapsed) {
    nodes.forEach(node => {
      if (node.type === 'directory')
        this._renderFolder(parent, node, collapsed)
      else
        this._renderFile(parent, node)
    })
  }

  _renderFolder(parent, node, collapsed) {
    const li = document.createElement('li')
    li.className = 'folder-item'
    li.dataset.folder = node.path
    if (collapsed.has(node.path))
      li.classList.add('collapsed')
    this._buildFolderContent(li, node, collapsed)
    parent.appendChild(li)
  }

  _buildFolderContent(li, node, collapsed) {
    const actions = this._canEdit() ? FileTree._folderActionsHtml() : ''
    li.innerHTML =
      `<div class="folder-header">${TOGGLE_ICON}` +
      `${FOLDER_ICON}<span>${escapeHtml(node.name)}</span>` +
      `${actions}</div>`
    const childList = document.createElement('ul')
    childList.className = 'folder-children'
    this._renderNodes(childList, node.children, collapsed)
    li.appendChild(childList)
  }

  static _folderActionsHtml() {
    return '<div class="file-actions">' +
      '<button class="icon-btn folder-rename" title="Rename">' +
      '<span class="material-symbols-outlined">' +
      'edit</span></button>' +
      '<button class="icon-btn folder-delete" title="Delete">' +
      '<span class="material-symbols-outlined">' +
      'delete</span></button></div>'
  }

  _renderFile(parent, node) {
    const li = document.createElement('li')
    li.className = 'file-item'
    li.dataset.file = node.path
    if (node.status === 'deleted')
      li.classList.add('file-deleted')
    li.innerHTML = this._fileItemHtml(node)
    if (this.app.currentFile === node.path)
      li.classList.add('active')
    parent.appendChild(li)
  }

  _fileItemHtml(node) {
    const status = node.status || this.app.gitStatuses[node.path]
    const badge = FileTree._badgeHtml(status)
    if (!this._canEdit())
      return `${FILE_ICON}<span>${escapeHtml(node.name)}</span>${badge}`
    const actions = FileTree._fileActionsHtml(status)
    return `${FILE_ICON}<span>${escapeHtml(node.name)}</span>${badge}${actions}`
  }

  static _badgeHtml(status) {
    if (!status)
      return ''
    return '<span class="material-symbols-outlined git-badge ' +
      `${STATUS_CLASSES[status]}">${STATUS_ICONS[status]}</span>`
  }

  static _fileActionsHtml(status) {
    let resetBtn = ''
    if (status && status !== 'untracked') {
      resetBtn = '<button class="icon-btn file-reset" title="Reset">' +
        '<span class="material-symbols-outlined">undo</span></button>'
    }
    return '<div class="file-actions">' +
      '<button class="icon-btn file-rename" title="Rename">' +
      '<span class="material-symbols-outlined">' +
      `edit</span></button>${resetBtn}` +
      '<button class="icon-btn file-delete" title="Delete">' +
      '<span class="material-symbols-outlined">' +
      'delete</span></button></div>'
  }

  _canEdit() {
    return this.app.bucketRole === 'editor'
      || this.app.bucketRole === 'committer'
  }

  /** Bind click events on the file tree. */

  bindTreeClicks() {
    this.app.els.fileTree.addEventListener('click', evt => {
      const folder = evt.target.closest('.folder-header')
      if (folder) {
        this._handleFolderClick(evt, folder)
        return
      }
      this._handleFileClick(evt)
    })
  }

  _handleFolderClick(evt, folder) {
    const folderItem = folder.closest('.folder-item')
    const folderPath = folderItem.dataset.folder
    if (evt.target.closest('.folder-delete'))
      this.actions.deleteFolder(folderPath)
    else if (evt.target.closest('.folder-rename'))
      this.actions.renameFolder(folderPath)
    else
      folderItem.classList.toggle('collapsed')
  }

  /** Bind drag-and-drop upload on the file explorer panel. */

  bindUploadDrop() {
    const zone = document.getElementById('file-explorer')
    zone.addEventListener('dragover', evt => {
      evt.preventDefault()
      if (this._canEdit())
        zone.classList.add('drop-active')
    })
    zone.addEventListener('dragleave', () => {
      zone.classList.remove('drop-active')
    })
    zone.addEventListener('drop', evt => {
      evt.preventDefault()
      zone.classList.remove('drop-active')
      if (this._canEdit() && evt.dataTransfer.files.length)
        this._uploadFiles(evt.dataTransfer.files, evt)
    })
  }

  async _uploadFiles(fileList, evt) {
    const folder = FileTree._dropTargetFolder(evt)
    await this.app.api.uploadFiles(
      this.app.bucket, fileList, folder,
    )
    await this.app.git.loadStatus()
    await this.loadFiles()
  }

  static _dropTargetFolder(evt) {
    const folderEl = evt.target.closest('.folder-item')
    return folderEl ? folderEl.dataset.folder : ''
  }

  _handleFileClick(evt) {
    const item = evt.target.closest('.file-item')
    if (!item)
      return
    const filePath = item.dataset.file
    if (evt.target.closest('.file-delete'))
      this.actions.deleteFile(filePath)
    else if (evt.target.closest('.file-rename'))
      this.actions.renameFile(filePath)
    else if (evt.target.closest('.file-reset'))
      this.actions.resetFile(filePath)
    else
      this.app.editor.openFile(filePath)
  }

}
