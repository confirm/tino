import { escapeHtml } from './constants.js'

const SECRET_WORD = 'clippy'
const LOGO_CLICKS = 5
const LOGO_WINDOW_MS = 1500

const NEXT = 1
const FADE_MS = 300
const IDLE_TIP_MS = 20000

const TIPS = [
  'It looks like you\'re writing a document. Would you like me to make it worse?',
  'It looks like you\'re using Typst. Have you considered Word 97 instead?',
  'Tip: #pagebreak() is cheaper than therapy.',
  'It looks like you forgot to commit. I won\'t tell anyone. Yet.',
  'Did you know? Every unclosed bracket makes a typesetter cry.',
  'It looks like you\'re trying to align a table. Good luck with that.',
  'I see you\'re editing {file}. Bold move. Literally: try *this*.',
  'Tip: Ctrl+S saves your file. Ctrl+Z saves your career.',
  'It looks like you\'re collaborating. Would you like me to blame someone?',
  'Fun fact: I was retired in 2007. TINO brought me back. Nobody asked.',
  'Have you tried turning the PDF off and on again?',
  'It looks like you\'re ignoring me. That\'s fine. I\'m used to it.',
]

/** Original paperclip drawing (one continuous wire, googly eyes, eyebrows). */

const SVG = `
<svg viewBox="0 0 80 124" class="clippy-svg" aria-hidden="true">
  <path class="clippy-wire"
    d="M50 40 V92 a8 8 0 0 1 -16 0 V24 a12 12 0 0 1 24 0 V100 a16 16 0 0 1 -32 0 V36"/>
  <g class="clippy-eyes">
    <path class="clippy-brow" d="M18 36 q8 -7 16 -1"/>
    <path class="clippy-brow" d="M46 33 q8 -6 16 1"/>
    <circle class="clippy-eye" cx="26" cy="48" r="8"/>
    <circle class="clippy-eye" cx="54" cy="47" r="8"/>
    <circle class="clippy-pupil" cx="28" cy="49" r="3.5"/>
    <circle class="clippy-pupil" cx="56" cy="48" r="3.5"/>
  </g>
</svg>`

/**
 * Easter egg: a paperclip assistant who offers unsolicited advice.
 * Summoned by clicking the logo five times quickly, or by typing "clippy"
 * outside text fields.
 */

export class Clippy {

  constructor(app) {
    this.app = app
    this._typed = ''
    this._clicks = []
    this._el = null
    this._tipIndex = -1
    this._idleTimer = null
  }

  /** Listen for logo clicks and the secret word. */

  bind() {
    this.app.els.logo.addEventListener('click', () => this._onLogoClick())
    document.addEventListener('keydown', evt => this._onKey(evt))
  }

  /** Summon the assistant, or show the next tip if already present. */

  summon() {
    if (!this._el)
      this._mount()
    this.nextTip()
  }

  /** Show the next tip in the speech bubble. */

  nextTip() {
    this._tipIndex = (this._tipIndex + NEXT) % TIPS.length
    const file = this.app.currentFile || 'nothing'
    const text = TIPS[this._tipIndex].replace('{file}', file)
    this._el.querySelector('.clippy-text').innerHTML = escapeHtml(text)
    this._el.classList.remove('clippy-bounce')
    requestAnimationFrame(() => this._el.classList.add('clippy-bounce'))
    this._scheduleIdleTip()
  }

  /** Send the assistant back into retirement. */

  dismiss() {
    if (!this._el)
      return
    const el = this._el
    this._el = null
    clearTimeout(this._idleTimer)
    el.classList.remove('visible')
    setTimeout(() => el.remove(), FADE_MS)
  }

  // ── Internal ──

  _onLogoClick() {
    const now = Date.now()
    this._clicks = this._clicks.filter(at => now - at < LOGO_WINDOW_MS)
    this._clicks.push(now)
    if (this._clicks.length < LOGO_CLICKS)
      return
    this._clicks = []
    this.summon()
  }

  _onKey(evt) {
    if (Clippy._isTyping(evt.target))
      return
    this._typed = (this._typed + evt.key.toLowerCase()).slice(-SECRET_WORD.length)
    if (this._typed !== SECRET_WORD)
      return
    this._typed = ''
    this.summon()
  }

  static _isTyping(target) {
    return Boolean(target.closest('input, textarea, [contenteditable], .cm-editor'))
  }

  _mount() {
    const el = document.createElement('div')
    el.className = 'clippy'
    el.innerHTML = '<div class="clippy-bubble">' +
      '<button class="clippy-close" title="Go away">&times;</button>' +
      '<p class="clippy-text"></p>' +
      '<div class="clippy-actions">' +
      '<button class="btn btn-small clippy-next">Tell me more</button>' +
      '<button class="btn btn-small clippy-nope">Don\'t show this tip again</button>' +
      `</div></div><div class="clippy-body" title="Poke">${SVG}</div>`
    document.body.appendChild(el)
    this._el = el
    this._bindMounted(el)
    requestAnimationFrame(() => el.classList.add('visible'))
  }

  _bindMounted(el) {
    el.querySelector('.clippy-close').addEventListener('click', () => this.dismiss())
    el.querySelector('.clippy-nope').addEventListener('click', () => this.dismiss())
    el.querySelector('.clippy-next').addEventListener('click', () => this.nextTip())
    el.querySelector('.clippy-body').addEventListener('click', () => this.nextTip())
  }

  _scheduleIdleTip() {
    clearTimeout(this._idleTimer)
    this._idleTimer = setTimeout(() => {
      if (this._el)
        this.nextTip()
    }, IDLE_TIP_MS)
  }

}
