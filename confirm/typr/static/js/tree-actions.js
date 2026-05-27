/**
 * Handles file and folder CRUD actions triggered from the tree:
 * delete, rename, reset, and folder equivalents.
 */

export class TreeActions {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  async deleteFile(filePath) {
    // eslint-disable-next-line no-alert
    if (!confirm(`Delete "${filePath}"?`))
      return

    /*
     * Close the tab BEFORE the API call. closeTab disconnects collab,
     * which flushes the room to disk. Deleting first would race the
     * flush and re-create the file.
     */

    if (this.app.currentFile === filePath)
      this.app.editor.closeTab(filePath)
    await this.app.api.deleteFile(
      this.app.bucket, filePath,
    )
    await this._refresh()
  }

  async renameFile(filePath) {
    // eslint-disable-next-line no-alert
    const name = prompt('Rename file:', filePath)
    if (!name || name.trim() === filePath)
      return

    // Close BEFORE rename: same collab flush race as deleteFile.
    if (this.app.currentFile === filePath)
      this.app.editor.closeTab(filePath)
    await this.app.api.renameFile(
      this.app.bucket, filePath, name.trim(),
    )
    await this._refresh()
    this.app.editor.openFile(name.trim())
  }

  async resetFile(filePath) {
    // eslint-disable-next-line no-alert
    if (!confirm(`Reset "${filePath}" to last commit?`))
      return
    const result = await this.app.api.gitRestore(
      this.app.bucket, 'HEAD', [filePath],
    )
    if (result.restored && result.restored.length)
      this._applyReset(filePath)
  }

  async _applyReset(filePath) {
    delete this.app.fileBuffers[filePath]
    this.app.dirty.delete(filePath)
    if (this.app.currentFile === filePath)
      this.app.editor.openFile(filePath)
    await this._refresh()
  }

  async deleteFolder(folderPath) {
    // eslint-disable-next-line no-alert
    if (!confirm(`Delete folder "${folderPath}" and all its contents?`))
      return
    await this.app.api.deleteDir(
      this.app.bucket, folderPath,
    )
    this._closeTabsUnder(folderPath)
    await this._refresh()
  }

  async renameFolder(folderPath) {
    // eslint-disable-next-line no-alert
    const name = prompt('Rename folder:', folderPath)
    if (!name || name.trim() === folderPath)
      return
    await this.app.api.renameDir(
      this.app.bucket, folderPath, name.trim(),
    )
    this._closeTabsUnder(folderPath)
    await this._refresh()
  }

  _closeTabsUnder(folderPath) {
    const prefix = `${folderPath}/`
    this.app.openTabs
      .filter(tp => tp.startsWith(prefix))
      .forEach(tp => this.app.editor.closeTab(tp))
  }

  async _refresh() {
    await this.app.git.loadStatus()
    await this.app.fileTree.loadFiles()
  }

}
