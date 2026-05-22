import { ZOOM_MAX, ZOOM_MIN, ZOOM_STEP, escapeHtml } from './constants.js'

/**
 * Manages preview rendering and zoom controls.
 */

export class PreviewManager {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  /**
   * Compile the current .typ file and render SVG pages
   * in the preview pane.
   */

  async update() {
    const isTyp = this.app.currentFile
      && this.app.currentFile.endsWith('.typ')
    document.getElementById('btn-pdf')
      .classList.toggle('hidden', !isTyp)
    if (isTyp)
      await this.compile()
    else
      this.clear()
  }

  /** Show a placeholder when the current file has no preview. */

  clear() {
    this.app.els.previewPage.innerHTML =
      '<p class="preview-empty">No preview available for this file.</p>'
  }

  /** Compile the current .typ file via the API and render SVG pages. */

  async compile() {
    if (!this.app.bucket || !this.app.currentFile)
      return
    const preview = this.app.els.previewPage
    try {
      const result = await this.app.api.compile(
        this.app.bucket,
        this.app.currentFile,
      )
      preview.innerHTML = ''
      result.pages.forEach(svg => {
        const page = document.createElement('div')
        page.className = 'preview-svg-page'
        page.innerHTML = svg
        preview.appendChild(page)
      })
    }
    catch (err) {
      preview.innerHTML =
        `<pre class="preview-error">${escapeHtml(err.message)}</pre>`
    }
  }

  /** Download the current .typ file as a compiled PDF. */

  downloadPdf() {
    if (!this.app.bucket || !this.app.currentFile)
      return
    const slug = encodeURIComponent(this.app.bucket)
    const path = this.app.currentFile
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
  }

}
