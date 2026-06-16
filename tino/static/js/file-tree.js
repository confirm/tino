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
import { TreeDrag } from './tree-drag.js'
import { TreeNewMenu } from './tree-new-menu.js'

/**
 * Manages the file explorer tree and bucket loading.
 */

export class FileTree {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this.actions = new TreeActions(app)
    this.bucketPicker = new BucketPicker(app)
    this.drag = new TreeDrag(app)
    this.newMenu = new TreeNewMenu(app)
    this.filePaths = new Set()
    this._nodes = []
  }

  /** Fetch all buckets and auto-select if only one. */

  async loadBuckets() {
    this._buckets = await this.app.api.listBuckets()
    this.app.els.bucketLabel.textContent = this.app.currentBucketLabel()

    if (this._buckets.length === SINGLE_ITEM) {
      const [only] = this._buckets
      this.app.els.bucketLabel.textContent = only.name || only.slug
      await this.app.selectBucket(only.slug, only.role)
    }
  }

  /** Empty the file tree (called when no bucket is selected). */

  clear() {
    this.filePaths = new Set()
    this._nodes = []
    this.app.els.fileTree.innerHTML = ''
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
    const files = await this.app.api.listFiles(this.app.bucket)
    this.filePaths = new Set(files.map(fl => fl.path))
    this._nodes = TreeBuilder.build(
      files, this.app.gitStatuses, this._canEdit(),
    )
    this._renderTree()
  }

  /** Re-render the tree, applying the current search filter. */

  _renderTree() {
    const query = this.app.els.fileSearch.value
      .trim().toLowerCase()
    const collapsed = query ? new Set() : this._getCollapsedPaths()
    const nodes = FileTree._filterNodes(this._nodes, query)
    const tree = this.app.els.fileTree
    this._canEditCached = this._canEdit()
    tree.innerHTML = ''
    this._renderNodes(tree, nodes, collapsed)
  }

  /** Recursively keep only nodes whose path matches the query. */

  static _filterNodes(nodes, query) {
    if (!query)
      return nodes
    const result = []
    nodes.forEach(node => {
      if (node.type === 'directory')
        FileTree._filterDir(result, node, query)
      else if (node.path.toLowerCase().includes(query))
        result.push(node)
    })
    return result
  }

  static _filterDir(result, node, query) {
    const children = FileTree._filterNodes(node.children, query)
    if (children.length) {
      result.push({
        children,
        name: node.name,
        path: node.path,
        status: node.status,
        type: node.type,
      })
    }
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
    if (this._canEditCached)
      li.draggable = true
    if (collapsed.has(node.path))
      li.classList.add('collapsed')
    this._buildFolderContent(li, node, collapsed)
    parent.appendChild(li)
  }

  _buildFolderContent(li, node, collapsed) {
    const actions = this._canEditCached ? FileTree._folderActionsHtml() : ''
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
      '<button class="icon-btn folder-new-file" title="New file">' +
      '<span class="material-symbols-outlined">' +
      'note_add</span></button>' +
      '<button class="icon-btn folder-new-folder" title="New folder">' +
      '<span class="material-symbols-outlined">' +
      'create_new_folder</span></button>' +
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
    else if (this._canEditCached)
      li.draggable = true
    li.innerHTML = this._fileItemHtml(node)
    if (this.app.currentFile === node.path)
      li.classList.add('active')
    parent.appendChild(li)
  }

  _fileItemHtml(node) {
    const status = node.status || this.app.gitStatuses[node.path]
    const icon = FileTree._leadingIconHtml(status)
    if (!this._canEditCached)
      return `${icon}<span>${escapeHtml(node.name)}</span>`
    const actions = FileTree._fileActionsHtml(status)
    return `${icon}<span>${escapeHtml(node.name)}</span>${actions}`
  }

  static _leadingIconHtml(status) {
    if (!status)
      return FILE_ICON
    return '<span class="material-symbols-outlined file-icon git-status ' +
      `${STATUS_CLASSES[status]}">${STATUS_ICONS[status]}</span>`
  }

  static _fileActionsHtml(status) {
    if (status === 'deleted') {
      return '<div class="file-actions">' +
        '<button class="icon-btn file-reset" title="Restore">' +
        '<span class="material-symbols-outlined">undo</span></button></div>'
    }
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

  /** Bind the file search input to re-render on typing. */

  bindSearch() {
    this.app.els.fileSearch.addEventListener(
      'input', () => this._renderTree(),
    )
  }

  /** Bind the "New" menu in the explorer header (file / folder / template). */

  bindNewMenu() {
    this.newMenu.bind()
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
    if (evt.target.closest('.folder-new-file'))
      this.actions.createFileInFolder(folderPath)
    else if (evt.target.closest('.folder-new-folder'))
      this.actions.createFolder(`${folderPath}/`)
    else if (evt.target.closest('.folder-delete'))
      this.actions.deleteFolder(folderPath)
    else if (evt.target.closest('.folder-rename'))
      this.actions.renameFolder(folderPath)
    else
      folderItem.classList.toggle('collapsed')
  }

  /** Bind drag-and-drop upload on the file explorer panel. */

  bindUploadDrop() {
    this.drag.bindUploadDrop()
  }

  /** Bind drag-and-drop events for moving files and folders in the tree. */

  bindTreeDrag() {
    this.drag.bindTreeDrag()
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
    else if (!item.classList.contains('file-deleted'))
      this.app.editor.openFile(filePath)
  }

}
