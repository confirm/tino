import { el, reviewThreadNode } from './review-nodes.js'
import { selectReviewRange, setReviewThreads } from './codemirror-review.js'
import { SINGLE_ITEM } from './constants.js'

const OPEN_STATUS = 'open'
const MAX_QUOTE_LENGTH = 500

export class ReviewManager {

  constructor(app) {
    this.app = app
    this.threads = []
    this.pendingAnchor = null
    this.showResolved = false
    this.els = {
      anchor: document.getElementById('review-compose-anchor'),
      body: document.getElementById('review-compose-body'),
      compose: document.getElementById('review-compose'),
      list: document.getElementById('review-list'),
      panel: document.getElementById('review-panel'),
      resolved: document.getElementById('btn-review-resolved'),
    }
  }

  bind() {
    document.getElementById('btn-review')
      .addEventListener('click', () => this.toggle())
    document.getElementById('btn-review-close')
      .addEventListener('click', () => this.toggle(false))
    document.getElementById('btn-review-compose-cancel')
      .addEventListener('click', () => this.cancelComposer())
    document.getElementById('btn-review-compose-submit')
      .addEventListener('click', () => this.submitComment())
    this.els.resolved.addEventListener('click', () => this.toggleResolved())
    this.els.list.addEventListener('click', evt => this._onListClick(evt))
  }

  get canEdit() {
    return ['editor', 'committer'].includes(this.app.bucketRole)
  }

  toggle(force) {
    const next = typeof force === 'boolean' ? force : this.els.panel.classList.contains('hidden')
    this.els.panel.classList.toggle('hidden', !next)
    document.getElementById('btn-review').classList.toggle('active', next)
    if (next)
      this.loadForCurrentFile()
  }

  async toggleResolved() {
    this.showResolved = !this.showResolved
    this.els.resolved.classList.toggle('active', this.showResolved)
    await this.loadForCurrentFile()
  }

  clear() {
    this.threads = []
    this.pendingAnchor = null
    setReviewThreads(this.app.els.editor.view, [])
    this._render()
  }

  async loadForCurrentFile() {
    if (!this.app.bucket || !this.app.currentFile || this.app.els.editor.hidden) {
      this.clear()
      return
    }
    const status = this.showResolved ? 'all' : OPEN_STATUS
    this.threads = await this.app.api.listComments(
      this.app.bucket, this.app.currentFile, status,
    )
    setReviewThreads(this.app.els.editor.view, this.threads)
    this._render()
  }

  openComposerFromSelection() {
    if (!this._canStartComment())
      return
    this._showComposer(this._anchorFromSelection())
  }

  _canStartComment() {
    if (!this.canEdit) {
      this.app.toast.error('Editor role required to comment')
      return false
    }
    if (!this.app.currentFile || this.app.els.editor.hidden) {
      this.app.toast.error('Open a text file before adding a comment')
      return false
    }
    return true
  }

  _showComposer(anchor) {
    this.pendingAnchor = anchor
    this.els.anchor.textContent = this._anchorText(anchor)
    this.els.body.value = ''
    this.els.compose.classList.remove('hidden')
    this.toggle(true)
    this.els.body.focus()
  }

  cancelComposer() {
    this.pendingAnchor = null
    this.els.body.value = ''
    this.els.compose.classList.add('hidden')
  }

  async submitComment() {
    const body = this.els.body.value.trim()
    if (!body || !this.pendingAnchor)
      return
    const thread = await this.app.api.createComment(
      this.app.bucket, this.app.currentFile, this.pendingAnchor, body,
    )
    this.cancelComposer()
    await this.loadForCurrentFile()
    this.jumpToThread(thread.id)
  }

  jumpToThread(threadId) {
    const thread = this.threads.find(item => item.id === threadId)
    if (!thread)
      return
    selectReviewRange(
      this.app.els.editor.view,
      thread.anchor.from_offset,
      thread.anchor.to_offset,
    )
  }

  async _onListClick(evt) {
    const button = evt.target.closest('[data-review-action]')
    const item = evt.target.closest('.review-thread')
    if (!item)
      return
    const threadId = item.dataset.thread
    if (!button) {
      if (evt.target.closest('input, textarea, select, label'))
        return
      this.jumpToThread(threadId)
      return
    }
    const action = button.dataset.reviewAction
    if (action === 'jump')
      this.jumpToThread(threadId)
    else if (action === 'resolve')
      await this._updateStatus(threadId, 'resolved')
    else if (action === 'reopen')
      await this._updateStatus(threadId, OPEN_STATUS)
    else if (action === 'reply')
      await this._reply(threadId, item)
  }

  async _updateStatus(threadId, status) {
    await this.app.api.updateComment(this.app.bucket, threadId, status)
    await this.loadForCurrentFile()
  }

  async _reply(threadId, item) {
    const input = item.querySelector('.review-reply-input')
    const body = input.value.trim()
    if (!body)
      return
    await this.app.api.replyToComment(this.app.bucket, threadId, body)
    input.value = ''
    await this.loadForCurrentFile()
  }

  _anchorFromSelection() {
    const ed = this.app.els.editor
    const { from, to } = ed.selection
    const start = Math.min(from, to)
    const end = Math.max(from, to)
    const { doc } = ed.view.state
    const startLine = doc.lineAt(start)
    const endLine = doc.lineAt(end)
    const quote = ReviewManager._quoteFor(ed.content, doc, start, end)
    return {
      column: start - startLine.from + SINGLE_ITEM,
      end_column: end - endLine.from + SINGLE_ITEM,
      end_line: endLine.number,
      from_offset: start,
      line: startLine.number,
      quote,
      to_offset: end,
    }
  }

  static _quoteFor(content, doc, start, end) {
    if (end > start)
      return content.slice(start, end).slice(0, MAX_QUOTE_LENGTH)
    return doc.lineAt(start).text.trim().slice(0, MAX_QUOTE_LENGTH)
  }

  _anchorText(anchor) {
    const path = this.app.currentFile
    if (anchor.line === anchor.end_line && anchor.column === anchor.end_column)
      return `${path}:${anchor.line}:${anchor.column}`
    if (anchor.line === anchor.end_line)
      return `${path}:${anchor.line}:${anchor.column}-${anchor.end_column}`
    return `${path}:${anchor.line}:${anchor.column}-${anchor.end_line}:${anchor.end_column}`
  }

  _render() {
    this.els.list.replaceChildren()
    if (!this.app.currentFile) {
      this.els.list.appendChild(el('li', 'review-empty', 'Open a text file to review.'))
      return
    }
    if (!this.threads.length) {
      const msg = this.showResolved ? 'No comments for this file.' : 'No open comments.'
      this.els.list.appendChild(el('li', 'review-empty', msg))
      return
    }
    for (const thread of this.threads)
      this.els.list.appendChild(reviewThreadNode(thread, this.canEdit, OPEN_STATUS))
  }

}
