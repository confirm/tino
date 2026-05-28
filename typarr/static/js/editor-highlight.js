const LANG = 'typst'

/**
 * Syntax-highlighted overlay rendered behind the editor textarea
 * using Prism.js. Mirrors the textarea content and scroll position.
 */

export class EditorHighlight {

  /**
   * @param {HTMLTextAreaElement} textarea - Source of truth for content.
   * @param {HTMLElement} target - The <code> element inside the overlay <pre>.
   */

  constructor(textarea, target) {
    this._ta = textarea
    this._code = target
    this._pre = target.parentElement
    this._ta.addEventListener('input', () => this.sync())
    this._ta.addEventListener('scroll', () => this._syncScroll())
  }

  /** Re-run Prism over the current value and update the overlay. */

  sync() {
    const { value } = this._ta
    const text = value.endsWith('\n') ? `${value} ` : value
    this._code.textContent = text
    const prism = window.Prism
    const lang = prism && prism.languages && prism.languages[LANG]
    if (lang)
      this._code.innerHTML = prism.highlight(text, lang, LANG)
    this._syncScroll()
  }

  _syncScroll() {
    this._pre.scrollTop = this._ta.scrollTop
    this._pre.scrollLeft = this._ta.scrollLeft
  }

}
