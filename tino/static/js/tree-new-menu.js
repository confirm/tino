/**
 * The "New" dropdown menu in the file-explorer header. Offers creating a file,
 * a folder, or a bucket from a template, delegating to the existing actions.
 */

export class TreeNewMenu {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._btn = document.getElementById('btn-tree-new')
    this._menu = document.getElementById('tree-new-menu')
  }

  /** Bind the toggle button, item clicks, and outside-click / Escape dismissal. */

  bind() {
    this._btn.addEventListener('click', evt => {
      evt.stopPropagation()
      this._toggle()
    })
    this._menu.addEventListener('click', evt => {
      const item = evt.target.closest('.tree-new-item')
      if (!item)
        return
      this._close()
      this._run(item.dataset.action)
    })
    document.addEventListener('click', () => this._close())
    document.addEventListener('keydown', evt => {
      if (evt.key === 'Escape')
        this._close()
    })
  }

  _toggle() {
    const willOpen = this._menu.classList.contains('hidden')
    this._menu.classList.toggle('hidden', !willOpen)
    this._btn.setAttribute('aria-expanded', String(willOpen))
  }

  _close() {
    if (this._menu.classList.contains('hidden'))
      return
    this._menu.classList.add('hidden')
    this._btn.setAttribute('aria-expanded', 'false')
  }

  _run(action) {
    if (action === 'file')
      this.app.editor.createNewFile()
    else if (action === 'folder')
      this.app.fileTree.actions.createFolder()
    else if (action === 'template')
      this.app.templatePicker.open()
  }

}
