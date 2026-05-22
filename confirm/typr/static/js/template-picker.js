import { escapeHtml } from './constants.js'

/**
 * Manages the template picker dialog: fetching, searching,
 * and initializing buckets from Typst templates.
 */

export class TemplatePicker {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._localTemplates = []
    this._universeTemplates = []
    this._activeTab = 'local'
    this._dialog = document.getElementById('template-dialog')
    this._list = document.getElementById('template-list')
    this._search = document.getElementById('template-search')
  }

  /** Open the dialog and load templates. */

  async open() {
    if (!this.app.bucket)
      return
    this._search.value = ''
    this._dialog.classList.add('visible')
    await this._loadAndRender()
  }

  /** Close the dialog. */

  close() {
    this._dialog.classList.remove('visible')
  }

  /** Bind all dialog events. */

  bind() {
    this._bindClose()
    this._bindSearch()
    this._bindListClicks()
    this._bindTabs()
  }

  /** @returns {object[]} Templates for the currently active tab. */

  get _activeTemplates() {
    if (this._activeTab === 'local')
      return this._localTemplates
    return this._universeTemplates
  }

  async _loadAndRender() {
    this._list.innerHTML = '<li class="template-loading">Loading…</li>'
    const [local, universe] = await Promise.all([
      this.app.api.listLocalTemplates(),
      this.app.api.listTemplates(),
    ])
    this._localTemplates = local
    this._universeTemplates = universe
    this._renderList(this._activeTemplates)
  }

  _renderList(templates) {
    this._list.innerHTML = ''
    templates.forEach(tpl => {
      this._list.appendChild(TemplatePicker._renderItem(tpl))
    })
    if (!templates.length) {
      this._list.innerHTML =
        '<li class="template-loading">No templates found.</li>'
    }
  }

  static _renderItem(tpl) {
    const li = document.createElement('li')
    li.className = 'template-item'
    li.dataset.name = tpl.name
    li.dataset.version = tpl.version
    li.dataset.namespace = tpl.namespace || 'preview'
    li.dataset.entrypoint = tpl.entrypoint || 'main.typ'
    const authors = (tpl.authors || [])
      .map(au => escapeHtml(au)).join(', ')
    li.innerHTML =
      '<div class="template-header">' +
      `<span class="template-name">${escapeHtml(tpl.name)}</span>` +
      `<span class="template-version">${escapeHtml(tpl.version)}</span>` +
      '</div>' +
      `<div class="template-desc">${escapeHtml(tpl.description)}</div>` +
      `<div class="template-authors">${authors}</div>`
    return li
  }

  _filterTemplates(query) {
    const lower = query.toLowerCase()
    const filtered = this._activeTemplates.filter(tpl =>
      tpl.name.toLowerCase().includes(lower)
      || tpl.description.toLowerCase().includes(lower))
    this._renderList(filtered)
  }

  async _selectTemplate(name, version, namespace, entrypoint) {
    try {
      await this.app.api.initTemplate(
        this.app.bucket, name, version, namespace,
      )
      this.close()
      await this.app.git.loadStatus()
      await this.app.fileTree.loadFiles()
      if (entrypoint)
        this.app.editor.openFile(entrypoint)
    }
    catch (err) {
      // eslint-disable-next-line no-alert
      alert(`Template init failed: ${err.message}`)
    }
  }

  _switchTab(tab) {
    this._activeTab = tab
    this._dialog.querySelectorAll('.template-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab)
    })
    this._search.value = ''
    this._renderList(this._activeTemplates)
  }

  _bindClose() {
    document.getElementById('btn-template-close')
      .addEventListener('click', () => this.close())
    this._dialog.addEventListener('click', evt => {
      if (evt.target === this._dialog)
        this.close()
    })
  }

  _bindSearch() {
    this._search.addEventListener('input', evt => {
      this._filterTemplates(evt.target.value)
    })
  }

  _bindListClicks() {
    this._list.addEventListener('click', evt => {
      const item = evt.target.closest('.template-item')
      if (item) {
        this._selectTemplate(
          item.dataset.name,
          item.dataset.version,
          item.dataset.namespace,
          item.dataset.entrypoint,
        )
      }
    })
  }

  _bindTabs() {
    this._dialog.querySelectorAll('.template-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this._switchTab(btn.dataset.tab)
      })
    })
  }

}
