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
 * Preview zoom: the zoom buttons and Ctrl/⌘ + wheel, keeping the content under
 * the viewport's centre (buttons) or the cursor (wheel) in place.
 */

export class PreviewZoom {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
  }

  /** Bind the zoom buttons and Ctrl/⌘ + wheel on the preview viewport. */

  bind() {
    // Buttons snap to the step grid, since wheel zoom leaves arbitrary levels.
    document.getElementById('btn-zoom-in')
      .addEventListener('click', () => {
        const below = Math.floor(this.app.zoom / ZOOM_STEP) * ZOOM_STEP
        this._setZoom(below + ZOOM_STEP)
      })

    document.getElementById('btn-zoom-out')
      .addEventListener('click', () => {
        const above = Math.ceil(this.app.zoom / ZOOM_STEP) * ZOOM_STEP
        this._setZoom(above - ZOOM_STEP)
      })

    document.getElementById('preview-viewport')
      .addEventListener('wheel', ev => this._onWheel(ev), { passive: false })
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
    this._setZoom(this.app.zoom * Math.exp(-pixels * ZOOM_WHEEL_SENSITIVITY), ev)
  }

}
