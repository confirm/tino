import { escapeHtml } from './constants.js'

const DISMISS_MS = 5000
const FADE_MS = 300

const ICONS = {
  error: 'error',
  info: 'info',
  success: 'check_circle',
}

/**
 * Non-blocking toast notifications that slide in from the bottom-right.
 * Replaces window.alert for a better editor UX.
 */

export class Toast {

  constructor() {
    this._container = null
  }

  /** Attach to the DOM container element. */

  bind() {
    this._container =
      document.getElementById('toast-container')
  }

  /** Show a red error toast. */

  error(message) {
    this._show(message, 'error')
  }

  /** Show a green success toast. */

  success(message) {
    this._show(message, 'success')
  }

  /** Show a blue informational toast. */

  info(message) {
    this._show(message, 'info')
  }

  // ── Internal ──

  _show(message, type) {
    const el = document.createElement('div')
    el.className = `toast toast-${type}`
    el.innerHTML = Toast._html(message, type)
    this._container.appendChild(el)
    requestAnimationFrame(() => el.classList.add('visible'))
    Toast._autoRemove(el)
    Toast._bindClose(el)
  }

  static _autoRemove(el) {
    setTimeout(() => Toast._remove(el), DISMISS_MS)
  }

  static _bindClose(el) {
    el.querySelector('.toast-close')
      .addEventListener('click', () => Toast._remove(el))
  }

  static _remove(el) {
    if (!el.parentNode)
      return
    el.classList.remove('visible')
    setTimeout(() => el.remove(), FADE_MS)
  }

  static _html(message, type) {
    const icon = ICONS[type] || 'info'
    return '<span class="material-symbols-outlined ' +
      `toast-icon">${icon}</span>` +
      '<span class="toast-message">' +
      `${escapeHtml(message)}</span>` +
      '<button class="toast-close">&times;</button>'
  }

}
