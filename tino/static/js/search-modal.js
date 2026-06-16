import {
  INDEX_NOT_FOUND,
  SEARCH_DEBOUNCE_MS,
  SEARCH_MIN_CHARS,
  SINGLE_ITEM,
  escapeHtml,
} from './constants.js'

/**
 * Global search modal. Searches file names and content across the buckets the
 * user can access, scoped to either the current bucket or all buckets. Clicking
 * a result opens the file (switching bucket if needed) and jumps to the line.
 */

export class SearchModal {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._scope = 'bucket'
    this._seq = 0
    this._timer = null
    this._dialog = document.getElementById('search-dialog')
    this._input = document.getElementById('search-input')
    this._results = document.getElementById('search-results')
  }

  /** Open the modal, defaulting the scope to the current bucket when present. */

  open() {
    this._setScope(this.app.bucket ? 'bucket' : 'all')
    document.getElementById('search-scope-bucket').disabled = !this.app.bucket
    this._input.value = ''
    this._renderEmpty('Type at least 2 characters to search.')
    this._dialog.classList.add('visible')
    this._input.focus()
  }

  /** Close the modal and cancel any pending search. */

  close() {
    this._dialog.classList.remove('visible')
    clearTimeout(this._timer)
  }

  /** Bind all modal events. */

  bind() {
    this._bindClose()
    this._bindInput()
    this._bindScope()
    this._bindResults()
  }

  _setScope(scope) {
    this._scope = scope
    this._dialog.querySelectorAll('.search-scope-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.scope === scope)
    })
  }

  _schedule() {
    clearTimeout(this._timer)
    this._timer = setTimeout(() => this._run(), SEARCH_DEBOUNCE_MS)
  }

  /** Run the search for the current query, ignoring stale (superseded) responses. */

  async _run() {
    const query = this._input.value.trim()
    if (query.length < SEARCH_MIN_CHARS) {
      this._renderEmpty('Type at least 2 characters to search.')
      return
    }
    this._seq += SINGLE_ITEM
    const seq = this._seq
    const bucket = this._scope === 'bucket' ? this.app.bucket : null
    const results = await this.app.api.search(query, bucket)
    if (seq === this._seq)
      this._render(results, query)
  }

  _renderEmpty(message) {
    this._results.innerHTML =
      `<li class="search-empty">${escapeHtml(message)}</li>`
  }

  _render(results, query) {
    if (!results.length) {
      this._renderEmpty('No matches found.')
      return
    }
    this._results.innerHTML = ''
    const showBucket = this._scope === 'all'
    results.forEach(result => {
      const label = this.app.bucketDisplayName(result.bucket)
      this._results.appendChild(
        SearchModal._renderItem(result, query, showBucket, label),
      )
    })
  }

  static _renderItem(result, query, showBucket, bucketLabel) {
    const li = document.createElement('li')
    li.className = 'search-result'
    li.dataset.bucket = result.bucket
    li.dataset.path = result.path
    let badge = ''
    if (showBucket)
      badge = `<span class="search-bucket-badge">${escapeHtml(bucketLabel)}</span>`
    const name = SearchModal._highlight(result.path, query)
    const snippets = result.snippets
      .map(snippet => SearchModal._renderSnippet(snippet, query)).join('')
    li.innerHTML =
      `<div class="search-result-path">${badge}` +
      '<span class="material-symbols-outlined">description</span>' +
      `<span>${name}</span></div>${snippets}`
    return li
  }

  static _renderSnippet(snippet, query) {
    const text = SearchModal._highlight(snippet.text, query)
    return `<div class="search-snippet" data-line="${snippet.line}">` +
      `<span class="search-snippet-line">${snippet.line}</span>` +
      `<span class="search-snippet-text">${text}</span></div>`
  }

  /** Escape HTML and wrap the first case-insensitive match of *query* in <mark>. */

  static _highlight(text, query) {
    const needle = query.toLowerCase()
    const idx = needle ? text.toLowerCase().indexOf(needle) : INDEX_NOT_FOUND
    if (idx === INDEX_NOT_FOUND)
      return escapeHtml(text)
    const end = idx + needle.length
    const before = escapeHtml(text.slice(0, idx))
    const hit = escapeHtml(text.slice(idx, end))
    const after = escapeHtml(text.slice(end))
    return `${before}<mark>${hit}</mark>${after}`
  }

  _bindClose() {
    document.getElementById('btn-search-close')
      .addEventListener('click', () => this.close())
    this._dialog.addEventListener('click', evt => {
      if (evt.target === this._dialog)
        this.close()
    })
    this._input.addEventListener('keydown', evt => {
      if (evt.key === 'Escape')
        this.close()
    })
  }

  _bindInput() {
    this._input.addEventListener('input', () => this._schedule())
  }

  _bindScope() {
    this._dialog.querySelectorAll('.search-scope-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (btn.disabled)
          return
        this._setScope(btn.dataset.scope)
        this._run()
      })
    })
  }

  _bindResults() {
    this._results.addEventListener('click', evt => {
      const item = evt.target.closest('.search-result')
      if (!item)
        return
      const snippet = evt.target.closest('.search-snippet')
      const line = snippet ? Number(snippet.dataset.line) : null
      this._openResult(item.dataset.bucket, item.dataset.path, line)
    })
  }

  /** Open a result file, switching bucket if needed, then jump to the line. */

  async _openResult(bucket, path, line) {
    this.close()
    if (bucket !== this.app.bucket) {
      const info = this.app.fileTree._buckets.find(bkt => bkt.slug === bucket)
      this.app.els.bucketLabel.textContent = (info && info.name) || bucket
      await this.app.selectBucket(bucket, info ? info.role : null)
    }
    await this.app.editor.openFile(path)
    if (line)
      this.app.els.editor.goToLine(line)
  }

}
