import { GitAPI, bucketPath } from './git-api.js'

/**
 * HTTP client for the TINO REST API.
 * Wraps all backend endpoints (buckets, files, git, compile).
 * Git endpoints live in GitAPI, which this class extends.
 */

export class TinoAPI extends GitAPI {

  config() {
    return this._fetch('/api/config')
  }

  /** @returns {Promise<{instructions: string}>} Server-wide MCP instructions (admin only). */

  mcpInstructions() {
    return this._fetch('/api/mcp/instructions')
  }

  // ── Auth ──

  /** @returns {Promise<{username: string, email: string, groups: string[]}>} */

  me() {
    return this._fetch('/api/me')
  }

  // ── Buckets ──

  /** @returns {Promise<Array>} List of all buckets. */

  listBuckets() {
    return this._fetch('/api/buckets')
  }

  /** Get metadata for a single bucket. */

  getBucket(slug) {
    return this._fetch(bucketPath(slug))
  }

  /** Create a new bucket. */

  createBucket(slug, data) {
    return this._json('POST', '/api/buckets', { slug, ...data })
  }

  /** Delete a bucket and its git repo. */

  deleteBucket(slug) {
    return this._fetch(bucketPath(slug), { method: 'DELETE' })
  }

  /** Update a bucket's metadata (description, access rules). */

  updateBucket(slug, data) {
    return this._json('PUT', bucketPath(slug), data)
  }

  // ── Files ──

  /** List all files in a bucket. */

  listFiles(slug) {
    return this._fetch(`${bucketPath(slug)}/files`)
  }

  /** Read a file's content. */

  readFile(slug, path) {
    return this._fetch(`${bucketPath(slug)}/files/${path}`)
  }

  /** Save (overwrite) a file's content. */

  saveFile(slug, path, content) {
    return this._json(
      'PUT', `${bucketPath(slug)}/files/${path}`, { content },
    )
  }

  /** Create a new file. Fails if it already exists. */

  createFile(slug, path, content) {
    return this._json(
      'POST', `${bucketPath(slug)}/files`, { content: content || '', path },
    )
  }

  /** Upload files via multipart form data. */

  uploadFiles(slug, fileList, prefix) {
    const form = new FormData()
    for (const file of fileList)
      form.append('files', file)
    const qp = prefix ? `?prefix=${encodeURIComponent(prefix)}` : ''
    return this._fetch(
      `${bucketPath(slug)}/files/upload${qp}`,
      { body: form, method: 'POST' },
    )
  }

  /** Create an empty directory. */

  createDir(slug, path) {
    return this._json(
      'POST', `${bucketPath(slug)}/files/mkdir`, { path },
    )
  }

  /** Delete a file from the bucket. */

  deleteFile(slug, path) {
    return this._fetch(
      `${bucketPath(slug)}/files/${path}`, { method: 'DELETE' },
    )
  }

  /** Delete a directory and all its contents. */

  deleteDir(slug, path) {
    return this._fetch(
      `${bucketPath(slug)}/files/dir/${path}`,
      { method: 'DELETE' },
    )
  }

  /** Rename/move a file. */

  renameFile(slug, oldPath, newPath) {
    const path = `${bucketPath(slug)}/files/rename`
    return this._json(
      'POST', path, { new_path: newPath, old_path: oldPath },
    )
  }

  /** Rename/move a directory. */

  renameDir(slug, oldPath, newPath) {
    const path = `${bucketPath(slug)}/files/rename-dir`
    return this._json(
      'POST', path, { new_path: newPath, old_path: oldPath },
    )
  }

  // ── Search ──

  /**
   * Search file names and content across accessible buckets.
   * @param {string} query - Search query.
   * @param {string} [bucket] - Limit to one bucket; omit to search all.
   */

  search(query, bucket) {
    const params = new URLSearchParams()
    params.set('q', query)
    if (bucket)
      params.set('bucket', bucket)
    return this._fetch(`/api/search?${params}`)
  }

  // ── Compile ──

  compile(slug, path) {
    return this._fetch(`${bucketPath(slug)}/compile/svg/${path}`)
  }

  // ── Templates ──

  /** Fetch templates from the Typst Universe package index. */

  listTypstUniverseTemplates() {
    return this._fetch('/api/templates/typst-universe')
  }

  /** Fetch templates from the local package directory. */

  listLocalTemplates() {
    return this._fetch('/api/templates/local')
  }

  /** Initialize a bucket from a Typst template. */

  initTemplate(slug, name, version, namespace, targetDir) {
    const path = `${bucketPath(slug)}/init-template`
    const body = { name, namespace: namespace || 'preview', version }
    if (targetDir)
      body.target_dir = targetDir
    return this._json('POST', path, body)
  }

  // ── API Keys ──

  /** List all API keys (metadata only). */

  listApiKeys() {
    return this._fetch('/api/keys')
  }

  /**
   * Create a new API key.
   * @param {string} label
   * @param {Object.<string,string>} access - Map of bucket slug → role.
   */

  createApiKey(label, access) {
    return this._json('POST', '/api/keys', { access, label })
  }

  /**
   * Update label and/or access for an existing key.
   * @param {string} keyId
   * @param {string} label
   * @param {Object.<string,string>} access
   */

  updateApiKey(keyId, label, access) {
    return this._json('PATCH', `/api/keys/${encodeURIComponent(keyId)}`, { access, label })
  }

  /** Revoke (permanently delete) an API key. */

  revokeApiKey(keyId) {
    return this._fetch(`/api/keys/${encodeURIComponent(keyId)}`, { method: 'DELETE' })
  }

  // ── Fonts ──

  /** List all installed custom fonts. */

  listFonts() {
    return this._fetch('/api/fonts')
  }

  /** Upload font files via multipart form data. */

  uploadFonts(fileList) {
    const form = new FormData()
    for (const file of fileList)
      form.append('files', file)
    return this._fetch('/api/fonts/upload', { body: form, method: 'POST' })
  }

  /** Delete a font by filename. */

  deleteFont(filename) {
    return this._fetch(
      `/api/fonts/${encodeURIComponent(filename)}`, { method: 'DELETE' },
    )
  }

}
