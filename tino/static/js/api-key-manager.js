import { escapeHtml } from './constants.js'

/**
 * Dialog for managing global API keys.
 * Admin-only feature — only shown when `app.isAdmin` is true.
 *
 * Three views:
 *  - list   — existing keys with revoke buttons
 *  - form   — create a new key (label + per-bucket access)
 *  - token  — one-time token reveal after creation
 */

export class ApiKeyManager {

  /** @param {import('./app.js').TinoApp} app */

  constructor(app) {
    this.app = app
    this._dialog = document.getElementById('apikey-dialog')
    this._list = document.getElementById('apikey-list')
    this._buckets = []
  }

  bind() {
    this._bindClose()
    this._bindForm()
    this._bindToken()
    this._bindList()
  }

  _bindClose() {
    document.getElementById('btn-apikey-close-x')
      .addEventListener('click', () => this.close())
    document.getElementById('btn-apikey-close')
      .addEventListener('click', () => this.close())
    this._dialog.addEventListener('click', evt => {
      if (evt.target === this._dialog)
        this.close()
    })
  }

  _bindForm() {
    document.getElementById('btn-apikey-new')
      .addEventListener('click', () => this._showForm())
    document.getElementById('btn-apikey-back')
      .addEventListener('click', () => this._showList())
    document.getElementById('btn-apikey-create')
      .addEventListener('click', () => this._createKey())
    document.getElementById('btn-apikey-access-add')
      .addEventListener('click', () => this._addAccessRow())
    document.getElementById('apikey-access-list')
      .addEventListener('click', evt => {
        if (evt.target.closest('.access-remove'))
          evt.target.closest('.access-row').remove()
      })
  }

  _bindToken() {
    document.getElementById('btn-apikey-copy')
      .addEventListener('click', () => this._copyToken())
    document.getElementById('btn-apikey-done')
      .addEventListener('click', () => this._showList())
  }

  _bindList() {
    this._list.addEventListener('click', evt => {
      const btn = evt.target.closest('[data-revoke]')
      if (btn)
        this._revoke(btn.dataset.revoke)
    })
  }

  async open() {
    this._dialog.classList.add('visible')
    this._buckets = await this.app.api.listBuckets().catch(() => [])
    await this._showList()
  }

  close() {
    this._dialog.classList.remove('visible')
  }

  // ── Views ──

  async _showList() {
    this._setTitle('API Keys')
    document.getElementById('apikey-view-list').classList.remove('hidden')
    document.getElementById('apikey-view-form').classList.add('hidden')
    document.getElementById('apikey-view-token').classList.add('hidden')
    await this._loadList()
  }

  _showForm() {
    this._setTitle('New API Key')
    document.getElementById('apikey-view-list').classList.add('hidden')
    document.getElementById('apikey-view-form').classList.remove('hidden')
    document.getElementById('apikey-view-token').classList.add('hidden')
    document.getElementById('apikey-form-label').value = ''
    document.getElementById('apikey-access-list').innerHTML = ''
    document.getElementById('apikey-form-label').focus()
  }

  _showToken(token) {
    this._setTitle('API Key Created')
    document.getElementById('apikey-view-list').classList.add('hidden')
    document.getElementById('apikey-view-form').classList.add('hidden')
    document.getElementById('apikey-view-token').classList.remove('hidden')
    document.getElementById('apikey-token-value').textContent = token
  }

  // eslint-disable-next-line class-methods-use-this
  _setTitle(text) {
    document.getElementById('apikey-dialog-title')
      .querySelector('span').textContent = text
  }

  // ── List ──

  async _loadList() {
    this._list.innerHTML = '<li class="font-empty">Loading…</li>'
    try {
      const keys = await this.app.api.listApiKeys()
      this._renderList(keys)
    }
    catch (err) {
      this._list.innerHTML = '<li class="font-empty">Failed to load API keys.</li>'
      this.app.toast.error(err.message)
    }
  }

  _renderList(keys) {
    if (!keys.length) {
      this._list.innerHTML = '<li class="font-empty">No API keys yet.</li>'
      return
    }
    this._list.innerHTML = keys.map(key => {
      const entries = Object.entries(key.access || {})
      const chips = entries.map(([slug, role]) =>
        `<span class="apikey-access-chip">${escapeHtml(slug)} → ${escapeHtml(role)}</span>`,
      ).join('')
      const noAccess = '<span class="apikey-no-access">no bucket access</span>'
      const accessHtml = entries.length ? chips : noAccess
      return '<li class="apikey-item">' +
          '<div class="apikey-item-header">' +
            `<span class="apikey-label">${escapeHtml(key.label)}</span>` +
            `<span class="apikey-id">${escapeHtml(key.id)}</span>` +
            `<span class="apikey-created">${escapeHtml(key.created)}</span>` +
            `<button class="icon-btn" data-revoke="${escapeHtml(key.id)}" title="Revoke key">` +
              '<span class="material-symbols-outlined">delete</span>' +
            '</button>' +
          '</div>' +
          `<div class="apikey-access-row">${accessHtml}</div>` +
        '</li>'
    }).join('')
  }

  async _revoke(keyId) {
    // eslint-disable-next-line no-alert
    if (!confirm('Revoke this API key? This cannot be undone.'))
      return
    try {
      await this.app.api.revokeApiKey(keyId)
      this.app.toast.success('API key revoked')
      await this._loadList()
    }
    catch (err) {
      this.app.toast.error(err.message)
    }
  }

  // ── Form ──

  _addAccessRow(slug = '', role = 'viewer') {
    const container = document.getElementById('apikey-access-list')
    const row = document.createElement('div')
    row.className = 'access-row'
    const options = this._buckets
      .map(bkt =>
        `<option value="${escapeHtml(bkt.slug)}"${bkt.slug === slug ? ' selected' : ''}>` +
        `${escapeHtml(bkt.slug)}</option>`,
      )
      .join('')
    row.innerHTML =
      `<select class="access-bucket">${options || '<option value="">—</option>'}</select>` +
      '<select class="access-role">' +
        '<option value="viewer">Viewer</option>' +
        '<option value="editor">Editor</option>' +
        '<option value="committer">Committer</option>' +
      '</select>' +
      '<button class="icon-btn access-remove" title="Remove">' +
        '<span class="material-symbols-outlined">close</span>' +
      '</button>'
    row.querySelector('.access-role').value = role
    container.appendChild(row)
  }

  // eslint-disable-next-line class-methods-use-this
  _collectAccess() {
    const rows = document.querySelectorAll('#apikey-access-list .access-row')
    const access = {}
    rows.forEach(row => {
      const slug = row.querySelector('.access-bucket').value
      const role = row.querySelector('.access-role').value
      if (slug && slug !== '—')
        access[slug] = role
    })
    return access
  }

  async _createKey() {
    const label = document.getElementById('apikey-form-label').value.trim()
    if (!label) {
      this.app.toast.error('Label is required.')
      return
    }
    const access = this._collectAccess()
    try {
      const result = await this.app.api.createApiKey(label, access)
      this._showToken(result.token)
    }
    catch (err) {
      this.app.toast.error(err.message)
    }
  }

  // ── Token reveal ──

  async _copyToken() {
    const token = document.getElementById('apikey-token-value').textContent
    try {
      await navigator.clipboard.writeText(token)
      this.app.toast.success('Token copied to clipboard')
    }
    catch {
      this.app.toast.error('Could not copy — please select and copy manually.')
    }
  }

}
