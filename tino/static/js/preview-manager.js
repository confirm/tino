import { SINGLE_ITEM, ZOOM_MAX, ZOOM_MIN, ZOOM_STEP, escapeHtml } from './constants.js'

/**
 * Manages preview rendering and zoom controls.
 */

export class PreviewManager {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  /** The file the preview renders: the pinned file, else the active file. */

  get target() {
    return this.app.pinnedPreview || this.app.currentFile
  }

  /**
   * Compile the preview target (the pinned file when one is pinned, otherwise
   * the current file) and render its SVG pages in the preview pane.
   */

  async update() {
    const isTyp = this.target && this.target.endsWith('.typ')
    this._renderPinControls()
    document.getElementById('btn-pdf')
      .classList.toggle('hidden', !isTyp)
    if (isTyp)
      await this.compile()
    else
      this.clear()
  }

  /** Pin the preview to the current .typ file, or unpin if already pinned. */

  togglePin() {
    if (this.app.pinnedPreview)
      this.app.pinnedPreview = null
    else if (this.app.currentFile && this.app.currentFile.endsWith('.typ'))
      this.app.pinnedPreview = this.app.currentFile
    this.update()
  }

  /** Sync the pin button and pinned-file label with the current pin state. */

  _renderPinControls() {
    const pinned = this.app.pinnedPreview
    const cur = this.app.currentFile
    const canPin = Boolean(pinned) || Boolean(cur && cur.endsWith('.typ'))
    const btn = document.getElementById('btn-pin-preview')
    btn.classList.toggle('hidden', !canPin)
    btn.classList.toggle('active', Boolean(pinned))
    btn.title = PreviewManager._pinTitle(pinned)
    PreviewManager._renderPinLabel(pinned)
  }

  static _pinTitle(pinned) {
    if (pinned)
      return `Preview pinned to ${pinned} — click to unpin`
    return 'Pin preview to this file'
  }

  static _renderPinLabel(pinned) {
    const label = document.getElementById('preview-pin-label')
    label.classList.toggle('hidden', !pinned)
    if (pinned)
      label.textContent = pinned
  }

  /** Show a placeholder when the current file has no preview. */

  clear() {
    this.app.els.previewPage.innerHTML =
      '<p class="preview-empty">No preview available for this file.</p>'
  }

  /** Compile the current .typ file via the API and render SVG pages. */

  async compile() {
    if (!this.app.bucket || !this.target)
      return
    this._renderGen = (this._renderGen || 0) + SINGLE_ITEM
    const gen = this._renderGen
    const preview = this.app.els.previewPage
    try {
      const result = await this.app.api.compile(this.app.bucket, this.target)
      if (gen === this._renderGen)
        PreviewManager._renderPages(preview, result.pages)
    }
    catch (err) {
      if (gen === this._renderGen) {
        preview.innerHTML =
          `<pre class="preview-error">${escapeHtml(err.message)}</pre>`
      }
    }
  }

  /** Build all SVG pages off-DOM and swap them in with a single reflow. */

  static _renderPages(preview, pages) {
    const fragment = document.createDocumentFragment()
    pages.forEach(svg => {
      const page = document.createElement('div')
      page.className = 'preview-svg-page'
      page.innerHTML = svg
      fragment.appendChild(page)
    })
    preview.replaceChildren(fragment)
  }

  /** Download the current .typ file as a compiled PDF. */

  downloadPdf() {
    if (!this.app.bucket || !this.target)
      return
    const slug = encodeURIComponent(this.app.bucket)
    const path = this.target
    const url = `/api/buckets/${slug}/compile/pdf/${path}`
    const link = document.createElement('a')
    link.href = url
    link.download = ''
    link.click()
  }

  /** Bind zoom in/out and PDF download buttons. */

  bindZoom() {
    const {previewPage, zoomLabel} = this.app.els

    document.getElementById('btn-zoom-in')
      .addEventListener('click', () => {
        if (this.app.zoom < ZOOM_MAX) {
          this.app.zoom += ZOOM_STEP
          previewPage.style.transform =
            `scale(${this.app.zoom / 100})`
          zoomLabel.textContent = `${this.app.zoom}%`
        }
      })

    document.getElementById('btn-zoom-out')
      .addEventListener('click', () => {
        if (this.app.zoom > ZOOM_MIN) {
          this.app.zoom -= ZOOM_STEP
          previewPage.style.transform =
            `scale(${this.app.zoom / 100})`
          zoomLabel.textContent = `${this.app.zoom}%`
        }
      })

    document.getElementById('btn-pdf')
      .addEventListener('click', () => this.downloadPdf())

    document.getElementById('btn-pin-preview')
      .addEventListener('click', () => this.togglePin())
  }

}
