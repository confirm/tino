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
    this.filePaths = new Set()
    this._nodes = []
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
    if (this._canEdit())
      li.draggable = true
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
    if (this._canEdit())
      li.draggable = true
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

  /** Bind the file search input to re-render on typing. */

  bindSearch() {
    this.app.els.fileSearch.addEventListener(
      'input', () => this._renderTree(),
    )
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
      if (evt.dataTransfer.types.includes('text/x-typr-path'))
        return
      evt.preventDefault()
      if (this._canEdit())
        this._highlightDropTarget(evt)
    })
    zone.addEventListener('dragleave', evt => {
      const related = evt.relatedTarget
      if (!related || !zone.contains(related))
        this._clearDropTargets()
    })
    zone.addEventListener('drop', evt => {
      if (evt.dataTransfer.types.includes('text/x-typr-path'))
        return
      evt.preventDefault()
      this._clearDropTargets()
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

  /** Bind drag-and-drop events for moving files and folders in the tree. */

  bindTreeDrag() {
    const tree = this.app.els.fileTree

    tree.addEventListener('dragstart', evt => {
      const item = evt.target.closest('.file-item') ||
        evt.target.closest('.folder-item')
      if (!item)
        return
      const path = item.dataset.file || item.dataset.folder
      const type = item.dataset.file ? 'file' : 'directory'
      evt.dataTransfer.setData('text/x-typr-path', path)
      evt.dataTransfer.setData('text/x-typr-type', type)
      evt.dataTransfer.effectAllowed = 'move'
    })

    tree.addEventListener('dragover', evt => {
      if (!evt.dataTransfer.types.includes('text/x-typr-path'))
        return
      evt.preventDefault()
      evt.dataTransfer.dropEffect = 'move'
      this._highlightDropTarget(evt)
    })

    tree.addEventListener('dragleave', evt => {
      const related = evt.relatedTarget
      if (!related || !tree.contains(related))
        this._clearDropTargets()
    })

    tree.addEventListener('drop', async evt => {
      if (!evt.dataTransfer.types.includes('text/x-typr-path'))
        return
      evt.preventDefault()
      evt.stopPropagation()
      this._clearDropTargets()
      const srcPath = evt.dataTransfer.getData('text/x-typr-path')
      const srcType = evt.dataTransfer.getData('text/x-typr-type')
      const destFolder = this._resolveDropFolder(evt)
      if (destFolder === null)
        return
      const name = srcPath.split('/').pop()
      const destPath = destFolder ? `${destFolder}/${name}` : name
      if (destPath === srcPath || destFolder.startsWith(srcPath + '/'))
        return
      try {
        if (srcType === 'file')
          await this._dropMoveFile(srcPath, destPath)
        else
          await this._dropMoveDir(srcPath, destPath)
      }
      catch (err) {
        this.app.toast.error(`Move failed: ${err.message}`)
      }
    })
  }

  async _dropMoveFile(srcPath, destPath) {
    if (this.app.currentFile === srcPath)
      this.app.editor.closeTab(srcPath)
    await this.app.api.renameFile(
      this.app.bucket, srcPath, destPath,
    )
    await this.actions._refresh()
  }

  async _dropMoveDir(srcPath, destPath) {
    this.actions._closeTabsUnder(srcPath)
    await this.app.api.renameDir(
      this.app.bucket, srcPath, destPath,
    )
    await this.actions._refresh()
  }

  _resolveDropFolder(evt) {
    const folder = evt.target.closest('.folder-item')
    if (folder)
      return folder.dataset.folder
    if (evt.target.closest('.file-tree') || evt.target.closest('.file-item'))
      return ''
    return null
  }

  _highlightDropTarget(evt) {
    this._clearDropTargets()
    const folder = evt.target.closest('.folder-item')
    if (folder)
      folder.classList.add('drop-target')
    else if (evt.target.closest('.file-tree'))
      this.app.els.fileTree.classList.add('drop-target-root')
  }

  _clearDropTargets() {
    this.app.els.fileTree
      .querySelectorAll('.drop-target')
      .forEach(el => el.classList.remove('drop-target'))
    this.app.els.fileTree.classList.remove('drop-target-root')
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
