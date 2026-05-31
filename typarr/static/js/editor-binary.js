import { escapeHtml } from './constants.js'

const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']

/**
 * Renders binary file previews with download links
 * and image display for the editor panel.
 */

export class BinaryPreview {

  /**
   * @param {TyparrApp} app - Main application instance.
   * @param {EditorToolbar} toolbar - Editor toolbar to hide for binary files.
   */

  constructor(app, toolbar) {
    this.app = app
    this.toolbar = toolbar
  }

  /** Show binary file preview with optional image and download link. */

  show(path) {
    this.toolbar.hide()
    this.app.els.editor.setHidden(true)
    const bp = this.app.els.binaryPreview
    const rawUrl = this._rawUrl(path)
    const name = path.split('/').pop()
    bp.innerHTML = BinaryPreview._html(path, rawUrl, name)
    bp.classList.remove('hidden')
  }

  _rawUrl(path) {
    const slug = encodeURIComponent(this.app.bucket)
    return `/api/buckets/${slug}/files/raw/${path}`
  }

  static _html(path, rawUrl, name) {
    const dl =
      `<a class="btn-download" href="${rawUrl}" ` +
      `download="${escapeHtml(name)}">` +
      '<span class="material-symbols-outlined">download</span>' +
      `Download ${escapeHtml(name)}</a>`
    if (BinaryPreview.isImage(path))
      return `<img src="${rawUrl}" alt="${escapeHtml(path)}">${dl}`
    return `<p>Binary file — cannot be edited here.</p>${dl}`
  }

  /** Check whether a path has an image extension. */

  static isImage(path) {
    const ext = path.split('.').pop().toLowerCase()
    return IMAGE_EXTS.includes(ext)
  }

}
