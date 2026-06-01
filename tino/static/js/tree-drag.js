/**
 * Handles drag-and-drop interactions in the file tree:
 * internal file/folder moves and external file uploads.
 */

export class TreeDrag {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  /** Bind drag-and-drop upload on the file explorer panel. */

  bindUploadDrop() {
    const zone = document.getElementById('file-explorer')
    zone.addEventListener('dragover', evt => {
      if (evt.dataTransfer.types.includes('text/x-tino-path'))
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
      if (evt.dataTransfer.types.includes('text/x-tino-path'))
        return
      evt.preventDefault()
      this._clearDropTargets()
      if (this._canEdit() && evt.dataTransfer.files.length)
        this._uploadFiles(evt.dataTransfer.files, evt)
    })
  }

  /** Bind drag-and-drop events for moving files and folders. */

  bindTreeDrag() {
    const tree = this.app.els.fileTree
    tree.addEventListener('dragstart', evt => {
      TreeDrag._onDragStart(evt)
    })
    tree.addEventListener('dragover', evt => {
      if (!evt.dataTransfer.types.includes('text/x-tino-path'))
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
    tree.addEventListener('drop', evt => {
      this._onTreeDrop(evt)
    })
  }

  static _onDragStart(evt) {
    const item = evt.target.closest('.file-item')
      || evt.target.closest('.folder-item')
    if (!item)
      return
    const path = item.dataset.file || item.dataset.folder
    const type = item.dataset.file ? 'file' : 'directory'
    evt.dataTransfer.setData('text/x-tino-path', path)
    evt.dataTransfer.setData('text/x-tino-type', type)
    evt.dataTransfer.effectAllowed = 'move'
  }

  async _onTreeDrop(evt) {
    if (!evt.dataTransfer.types.includes('text/x-tino-path'))
      return
    evt.preventDefault()
    evt.stopPropagation()
    this._clearDropTargets()
    const srcPath = evt.dataTransfer.getData('text/x-tino-path')
    const srcType = evt.dataTransfer.getData('text/x-tino-type')
    await this._moveDraggedItem(srcPath, srcType, evt)
  }

  async _moveDraggedItem(srcPath, srcType, evt) {
    const destFolder = TreeDrag._resolveDropFolder(evt)
    if (destFolder === null)
      return
    const name = srcPath.split('/').pop()
    const destPath = destFolder ? `${destFolder}/${name}` : name
    if (destPath === srcPath
      || destFolder.startsWith(`${srcPath}/`))
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
  }

  async _uploadFiles(fileList, evt) {
    const folder = TreeDrag._dropTargetFolder(evt)
    await this.app.api.uploadFiles(
      this.app.bucket, fileList, folder,
    )
    await this.app.git.loadStatus()
    await this.app.fileTree.loadFiles()
  }

  static _dropTargetFolder(evt) {
    const folderEl = evt.target.closest('.folder-item')
    return folderEl ? folderEl.dataset.folder : ''
  }

  async _dropMoveFile(srcPath, destPath) {
    if (this.app.currentFile === srcPath)
      this.app.editor.closeTab(srcPath)
    await this.app.api.renameFile(
      this.app.bucket, srcPath, destPath,
    )
    await this.app.fileTree.actions._refresh()
  }

  async _dropMoveDir(srcPath, destPath) {
    this.app.fileTree.actions._closeTabsUnder(srcPath)
    await this.app.api.renameDir(
      this.app.bucket, srcPath, destPath,
    )
    await this.app.fileTree.actions._refresh()
  }

  static _resolveDropFolder(evt) {
    const folder = evt.target.closest('.folder-item')
    if (folder)
      return folder.dataset.folder
    if (evt.target.closest('.file-tree')
      || evt.target.closest('.file-item'))
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

  _canEdit() {
    return this.app.bucketRole === 'editor'
      || this.app.bucketRole === 'committer'
  }

}
