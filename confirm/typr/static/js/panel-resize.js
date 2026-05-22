import { PANEL_MAX_WIDTH, PANEL_MIN_WIDTH } from './constants.js'

const STORAGE_KEY = 'typr:panel-widths'

/**
 * Manages drag-to-resize handles for workspace panels.
 * Panel widths are persisted in localStorage across sessions.
 */

export class PanelResize {

  constructor() {
    this.handles = []
    this.activeHandle = null
    this._panels = {}
  }

  /**
   * Attach a resize handle to a target panel and restore any saved width.
   * @param {string} handleId - DOM id of the drag handle.
   * @param {Function} getTarget - Returns the panel element.
   * @param {string} direction - 'left' or 'right'.
   */

  init(handleId, getTarget, direction) {
    const handle = document.getElementById(handleId)
    this.handles.push(handle)
    this._panels[handleId] = { direction, getTarget }
    PanelResize._restoreWidth(handleId, getTarget())
    handle.addEventListener('mousedown', evt => {
      this._onDragStart(evt, handle, getTarget, direction, handleId)
    })
  }

  static _restoreWidth(handleId, target) {
    const saved = PanelResize._loadWidths()
    if (saved[handleId]) {
      target.style.width = `${saved[handleId]}px`
      target.style.flex = 'none'
    }
  }

  _onDragStart(evt, handle, getTarget, direction, handleId) {
    evt.preventDefault()
    this.activeHandle = handle
    const target = getTarget()
    const startX = evt.clientX
    const startWidth = target.getBoundingClientRect().width
    handle.classList.add('active')
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    this._attachDragListeners(
      handle, target, startX, startWidth, { dir: direction, handleId },
    )
  }

  _attachDragListeners(handle, target, startX, startWidth, { dir, handleId }) {
    const isLeft = dir === 'left'
    const HALF = 2
    const maxWidth = isLeft ? PANEL_MAX_WIDTH : window.innerWidth / HALF
    const move = moveEvt => {
      const dx = moveEvt.clientX - startX
      const nw = isLeft ? startWidth + dx : startWidth - dx
      if (nw >= PANEL_MIN_WIDTH && nw <= maxWidth) {
        target.style.width = `${nw}px`
        target.style.flex = 'none'
      }
    }
    const up = () => {
      this.activeHandle = null
      handle.classList.remove('active')
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      PanelResize._saveWidth(handleId, target.getBoundingClientRect().width)
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  }

  static _loadWidths() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
    }
    catch {
      return {}
    }
  }

  static _saveWidth(handleId, width) {
    const saved = PanelResize._loadWidths()
    saved[handleId] = Math.round(width)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
  }

}
