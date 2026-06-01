import { escapeHtml } from './constants.js'

const KB = 1024
const MB = 1048576
const DECIMALS = 1

export class FontManager {

  /** @param {TinoApp} app */

  constructor(app) {
    this.app = app
    this._dialog = document.getElementById('font-dialog')
    this._list = document.getElementById('font-list')
    this._input = document.getElementById('font-upload-input')
  }

  bind() {
    document.getElementById('btn-font-close')
      .addEventListener('click', () => this.close())
    this._dialog.addEventListener('click', evt => {
      if (evt.target === this._dialog)
        this.close()
    })
    document.getElementById('btn-font-upload')
      .addEventListener('click', () => this._input.click())
    this._input.addEventListener('change', () => this._handleUpload())
    this._list.addEventListener('click', evt => {
      const btn = evt.target.closest('[data-delete]')
      if (btn)
        this._delete(btn.dataset.delete)
    })
  }

  async open() {
    this._dialog.classList.add('visible')
    await this._load()
  }

  close() {
    this._dialog.classList.remove('visible')
  }

  async _load() {
    this._list.innerHTML = '<li class="font-empty">Loading…</li>'
    try {
      const fonts = await this.app.api.listFonts()
      this._render(fonts)
    }
    catch (err) {
      this._list.innerHTML = '<li class="font-empty">Failed to load fonts.</li>'
      this.app.toast.error(err.message)
    }
  }

  _render(fonts) {
    if (!fonts.length) {
      this._list.innerHTML = '<li class="font-empty">No fonts installed.</li>'
      return
    }
    this._list.innerHTML = fonts.map(font =>
      '<li class="font-item">' +
        `<span class="font-name">${escapeHtml(font.filename)}</span>` +
        `<span class="font-size">${FontManager._formatSize(font.size)}</span>` +
        `<button class="icon-btn" data-delete="${escapeHtml(font.filename)}" title="Delete">` +
          '<span class="material-symbols-outlined">delete</span>' +
        '</button>' +
      '</li>',
    ).join('')
  }

  async _handleUpload() {
    const { files } = this._input
    if (!files.length)
      return
    try {
      await this.app.api.uploadFonts(files)
      this.app.toast.success('Fonts uploaded')
      await this._load()
    }
    catch (err) {
      this.app.toast.error(err.message)
    }
    this._input.value = ''
  }

  async _delete(filename) {
    // eslint-disable-next-line no-alert
    if (!confirm(`Delete font "${filename}"?`))
      return
    try {
      await this.app.api.deleteFont(filename)
      this.app.toast.success('Font deleted')
      await this._load()
    }
    catch (err) {
      this.app.toast.error(err.message)
    }
  }

  static _formatSize(bytes) {
    if (bytes < KB)
      return `${bytes} B`
    if (bytes < MB)
      return `${(bytes / KB).toFixed(DECIMALS)} KB`
    return `${(bytes / MB).toFixed(DECIMALS)} MB`
  }

}
