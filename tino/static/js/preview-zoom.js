import {
  SINGLE_ITEM,
  WHEEL_LINE_PX,
  ZOOM_MAX,
  ZOOM_MIN,
  ZOOM_STEP,
  ZOOM_WHEEL_SENSITIVITY,
} from './constants.js'

/** Divisor for the viewport's centre. */

const HALF = 2

/**
 * Preview zoom: the zoom buttons, fit to width, reset to 100% and Ctrl/⌘ +
 * wheel, keeping the content under the viewport's centre (buttons) or the
 * cursor (wheel) in place.
 */

export class PreviewZoom {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._fitWidth = false
  }

  /** Bind the zoom controls and Ctrl/⌘ + wheel on the preview viewport. */

  bind() {
    const viewport = document.getElementById('preview-viewport')

    // Buttons snap to the step grid, since wheel zoom leaves arbitrary levels.
    document.getElementById('btn-zoom-in')
      .addEventListener('click', () => {
        const below = Math.floor(this.app.zoom / ZOOM_STEP) * ZOOM_STEP
        this._manualZoom(below + ZOOM_STEP)
      })

    document.getElementById('btn-zoom-out')
      .addEventListener('click', () => {
        const above = Math.ceil(this.app.zoom / ZOOM_STEP) * ZOOM_STEP
        this._manualZoom(above - ZOOM_STEP)
      })

    document.getElementById('zoom-level')
      .addEventListener('click', () => this._manualZoom(100))

    document.getElementById('btn-zoom-fit')
      .addEventListener('click', () => this._enableFitWidth())

    viewport.addEventListener('wheel', ev => this._onWheel(ev), { passive: false })

    // Keep fitting while the panel is resized (or a scrollbar appears).
    new ResizeObserver(() => {
      if (this._fitWidth)
        this._fit()
    }).observe(viewport)
  }

  /** Zoom to an explicit level, which ends fit-to-width mode. */

  _manualZoom(zoom, anchor) {
    this._fitWidth = false
    document.getElementById('btn-zoom-fit').classList.remove('active')
    this._setZoom(zoom, anchor)
  }

  /** Fit the page to the preview's width, and keep it fitted until the next manual zoom. */

  _enableFitWidth() {
    this._fitWidth = true
    document.getElementById('btn-zoom-fit').classList.add('active')
    this._fit()
  }

  /**
   * Zoom so the page fills the viewport's inner width (between its paddings).
   * Zooming can add or remove the vertical scrollbar, which changes that width,
   * so it fits a second time when the width changed (reading `clientWidth`
   * forces the layout, so this doesn't depend on the ResizeObserver firing).
   */

  _fit() {
    const viewport = document.getElementById('preview-viewport')
    const before = viewport.clientWidth
    this._setZoom(this._fitZoom(viewport))
    if (viewport.clientWidth !== before)
      this._setZoom(this._fitZoom(viewport))
  }

  /**
   * The zoom at which the page fills the viewport's inner width. The page's
   * unzoomed width is derived from its current size, so this works for any
   * page format; the result is clamped like every other zoom level.
   */

  _fitZoom(viewport) {
    const style = getComputedStyle(viewport)
    const available = viewport.clientWidth
      - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight)
    const width = this.app.els.previewPage.getBoundingClientRect().width / (this.app.zoom / 100)
    return available / width * 100
  }

  /**
   * Apply a zoom level, keeping the content under an anchor point in place.
   *
   * The page is scaled with CSS `zoom` rather than a transform: it changes the
   * layout size, so a zoomed page can be scrolled in every direction (a
   * transform grows past the viewport's left edge, where it can't be reached).
   * The anchor's relative position within the page is measured before and
   * restored after zooming by scrolling, so centring and padding are handled
   * by the layout itself. No transition: mid-animation the scrollable area
   * would still be the old size and the browser would clamp the scroll.
   * @param {number} zoom - New zoom percentage (clamped to the allowed range).
   * @param {{clientX: number, clientY: number}} [anchor] - Client coordinates
   *   to keep in place (e.g. a WheelEvent); defaults to the viewport's centre.
   */

  _setZoom(zoom, anchor) {
    const { previewPage, zoomLabel } = this.app.els
    const viewport = document.getElementById('preview-viewport')
    const point = anchor || PreviewZoom._viewportCentre(viewport)
    const relative = PreviewZoom._relativePosition(previewPage, point)
    const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom))

    previewPage.style.zoom = clamped / 100
    PreviewZoom._scrollToRelative(viewport, previewPage, point, relative)
    this.app.zoom = clamped
    zoomLabel.textContent = `${Math.round(clamped)}%`
  }

  /** @returns {{clientX: number, clientY: number}} The viewport's centre. */

  static _viewportCentre(viewport) {
    const bounds = viewport.getBoundingClientRect()
    return {
      clientX: bounds.left + viewport.clientWidth / HALF,
      clientY: bounds.top + viewport.clientHeight / HALF,
    }
  }

  /** @returns {{left: number, top: number}} Where a point lies within the page (0–1). */

  static _relativePosition(page, point) {
    const rect = page.getBoundingClientRect()
    return {
      left: (point.clientX - rect.left) / (rect.width || SINGLE_ITEM),
      top: (point.clientY - rect.top) / (rect.height || SINGLE_ITEM),
    }
  }

  /** Scroll so the page's relative position lands back under the point. */

  static _scrollToRelative(viewport, page, point, relative) {
    const rect = page.getBoundingClientRect()
    viewport.scrollLeft += rect.left + relative.left * rect.width - point.clientX
    viewport.scrollTop += rect.top + relative.top * rect.height - point.clientY
  }

  /**
   * Ctrl/⌘ + wheel (and trackpad pinch, which browsers report as Ctrl +
   * wheel) zooms around the cursor. The zoom changes exponentially with the
   * scroll distance, so mouse wheel notches and fine trackpad deltas both feel
   * proportional. The browser's own page zoom is suppressed.
   * @param {WheelEvent} ev - The wheel event on the preview viewport.
   */

  _onWheel(ev) {
    if (!ev.ctrlKey && !ev.metaKey)
      return
    ev.preventDefault()
    const lines = ev.deltaMode === WheelEvent.DOM_DELTA_LINE
    const pixels = ev.deltaY * (lines ? WHEEL_LINE_PX : SINGLE_ITEM)
    this._manualZoom(this.app.zoom * Math.exp(-pixels * ZOOM_WHEEL_SENSITIVITY), ev)
  }

}
