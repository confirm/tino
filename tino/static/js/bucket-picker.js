import { escapeHtml } from './constants.js'

/**
 * Manages the bucket picker dialog and bucket CRUD form.
 */

export class BucketPicker {

  /** @param {TinoApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._editingSlug = null
  }

  /** Open the bucket picker dialog and populate the list. */

  async open() {
    this._showListView()
    await this._renderList()
    document.getElementById('btn-bucket-new')
      .classList.toggle('hidden', !this.app.isAdmin)
    this.app.els.bucketPicker.classList.add('visible')
  }

  /** Close the bucket picker overlay. */

  close() {
    this.app.els.bucketPicker.classList.remove('visible')
  }

  /** Bind click events for the bucket picker, form buttons, and close. */

  bind() {
    this._bindPickerClicks()
    this._bindFormButtons()
    this._bindClose()
  }

  async _renderList() {
    this._buckets = await this.app.api.listBuckets()
    const list = this.app.els.bucketPickerList
    list.innerHTML = ''
    let adminBtns = ''
    if (this.app.isAdmin) {
      adminBtns = '<button class="icon-btn bucket-edit">' +
        '<span class="material-symbols-outlined">settings</span></button>' +
        '<button class="icon-btn bucket-delete">' +
        '<span class="material-symbols-outlined">delete</span></button>'
    }
    this._buckets.forEach(bkt => {
      const li = document.createElement('li')
      li.className = 'bucket-pick'
      li.dataset.slug = bkt.slug
      const desc = bkt.description ? '<div class="bucket-pick-desc">' +
        `${escapeHtml(bkt.description).replace(/\n/gu, '<br>')}</div>` : ''
      li.innerHTML =
        '<div class="bucket-pick-header">' +
        '<span class="material-symbols-outlined">' +
        'database</span>' +
        '<span class="bucket-pick-name">' +
        `${escapeHtml(bkt.slug)}</span>${adminBtns}` +
        `</div>${desc}`
      list.appendChild(li)
    })
  }

  _bindPickerClicks() {
    this.app.els.bucketPickerList
      .addEventListener('click', evt => {
        const item = evt.target.closest('.bucket-pick')
        if (!item)
          return
        const { slug } = item.dataset
        if (evt.target.closest('.bucket-edit'))
          this._openEditForm(slug)
        else if (evt.target.closest('.bucket-delete'))
          this._deleteBucket(slug)
        else
          this._selectFromPicker(slug)
      })
  }

  _selectFromPicker(slug) {
    const bkt = this._buckets.find(item => item.slug === slug)
    this.app.els.bucketLabel.textContent = slug
    this.close()
    this.app.selectBucket(slug, bkt ? bkt.role : null)
  }

  _bindClose() {
    document.getElementById('btn-picker-close')
      .addEventListener('click', () => {
        this.close()
      })
    document.getElementById('btn-picker-close-x')
      .addEventListener('click', () => {
        this.close()
      })
    this.app.els.bucketPicker
      .addEventListener('click', evt => {
        if (evt.target === this.app.els.bucketPicker)
          this.close()
      })
  }

  // ── Bucket form (edit/create) ──

  _showListView() {
    this.app.els.bucketDialogTitle
      .querySelector('span').textContent = 'Select Bucket'
    document.getElementById('bucket-view-list')
      .classList.remove('hidden')
    document.getElementById('bucket-view-form')
      .classList.add('hidden')
    document.getElementById('btn-bucket-new')
      .classList.toggle('hidden', !this.app.isAdmin)
    this._editingSlug = null
  }

  _showFormView(bucket) {
    const isNew = !bucket
    this.app.els.bucketDialogTitle
      .querySelector('span').textContent =
      isNew ? 'New Bucket' : `Edit: ${bucket.slug}`
    document.getElementById('bucket-view-list')
      .classList.add('hidden')
    document.getElementById('bucket-view-form')
      .classList.remove('hidden')
    this._populateFormFields(bucket, isNew)
  }

  _populateFormFields(bucket, isNew) {
    const slugInput = this.app.els.bucketFormSlug
    slugInput.value = isNew ? '' : bucket.slug
    slugInput.readOnly = !isNew
    this.app.els.bucketFormDesc.value =
      isNew ? '' : bucket.description || ''
    this.app.els.bucketFormMcp.value =
      isNew ? '' : bucket.mcp_instructions || ''
    this._editingSlug = isNew ? null : bucket.slug
    BucketPicker._renderAccessList(bucket ? bucket.access : [])
    if (isNew)
      slugInput.focus()
    else
      this.app.els.bucketFormDesc.focus()
  }

  static _renderAccessList(entries) {
    const list = document.getElementById('bucket-access-list')
    list.innerHTML = ''
    entries.forEach(entry => {
      BucketPicker._addAccessRow(list, entry.group, entry.role)
    })
  }

  static _addAccessRow(list, group, role) {
    const container = list || document.getElementById('bucket-access-list')
    const row = document.createElement('div')
    row.className = 'access-row'
    row.innerHTML =
      '<input class="form-input access-group" ' +
      `type="text" placeholder="Group" value="${group || ''}">` +
      '<select class="access-role">' +
      '<option value="viewer">Viewer</option>' +
      '<option value="editor">Editor</option>' +
      '<option value="committer">Committer</option>' +
      '</select>' +
      '<button class="icon-btn access-remove">' +
      '<span class="material-symbols-outlined">' +
      'close</span></button>'
    const select = row.querySelector('select')
    if (role)
      select.value = role
    container.appendChild(row)
  }

  static _collectAccessEntries() {
    const rows = document.querySelectorAll(
      '#bucket-access-list .access-row',
    )
    const entries = []
    rows.forEach(row => {
      const group = row.querySelector('.access-group').value.trim()
      const role = row.querySelector('.access-role').value
      if (group)
        entries.push({ group, role })
    })
    return entries
  }

  _validateSlug(slug) {
    if (!slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(slug)) {
      this.app.toast.error('Slug must be lowercase alphanumeric with hyphens (e.g. "my-bucket").')
      return false
    }
    return true
  }

  async _saveBucket() {
    const slug = this.app.els.bucketFormSlug.value.trim()
    const description = this.app.els.bucketFormDesc.value.trim()
    const mcpInstructions = this.app.els.bucketFormMcp.value.trim()
    const access = BucketPicker._collectAccessEntries()
    if (!this._validateSlug(slug))
      return
    const update = { access, description, mcp_instructions: mcpInstructions }
    if (this._editingSlug)
      await this.app.api.updateBucket(this._editingSlug, update)
    else
      await this.app.api.createBucket(slug, description, access, mcpInstructions)
    await this.app.fileTree.loadBuckets()
    this._showListView()
    await this._renderList()
  }

  async _deleteBucket(slug) {
    // eslint-disable-next-line no-alert
    if (!confirm(`Delete bucket "${slug}"?`))
      return
    await this.app.api.deleteBucket(slug)
    if (this.app.bucket === slug) {
      this.app.bucket = null
      this.app.editor.resetState()
    }
    await this._renderList()
    await this.app.fileTree.loadBuckets()
  }

  async _openEditForm(slug) {
    const bucket = await this.app.api.getBucket(slug)
    this._showFormView(bucket)
  }

  _bindFormButtons() {
    document.getElementById('btn-bucket-new')
      .addEventListener('click', () => {
        this._showFormView(null)
      })
    document.getElementById('btn-bucket-save')
      .addEventListener('click', () => {
        this._saveBucket()
      })
    document.getElementById('btn-bucket-back')
      .addEventListener('click', () => {
        this._showListView()
        this._renderList()
      })
    document.getElementById('btn-access-add')
      .addEventListener('click', () => {
        BucketPicker._addAccessRow(null, '', 'viewer')
      })
    document.getElementById('bucket-access-list')
      .addEventListener('click', evt => {
        if (evt.target.closest('.access-remove'))
          evt.target.closest('.access-row').remove()
      })
  }

}
