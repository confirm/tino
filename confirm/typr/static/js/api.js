import { HTTP_NO_CONTENT } from './constants.js'

/**
 * HTTP client for the Typr REST API.
 * Wraps all backend endpoints (buckets, files, git, compile).
 */

export class TyprAPI {

  /** @param {string} [baseUrl] - Base URL of the backend. */

  constructor(baseUrl) {
    this.baseUrl = baseUrl || ''
  }

  /**
   * Internal fetch wrapper. Throws on non-OK responses,
   * returns parsed JSON or null for 204 No Content.
   */

  async _fetch(path, options) {
    const res = await fetch(this.baseUrl + path, options)
    if (!res.ok) {
      const body = await res.text()
      throw new Error(`${res.status}: ${body}`)
    }
    if (res.status === HTTP_NO_CONTENT)
      return null
    return res.json()
  }

  /** Send a JSON-body request (POST/PUT). */

  _json(method, path, data) {
    return this._fetch(path, {
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
      method,
    })
  }

  /** @returns {string} Encoded bucket API base path. */

  static _bucketPath(slug) {
    return `/api/buckets/${encodeURIComponent(slug)}`
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
    return this._fetch(TyprAPI._bucketPath(slug))
  }

  /** Create a new bucket. */

  createBucket(slug, description, access) {
    return this._json('POST', '/api/buckets', {
      access: access || [],
      description: description || '',
      slug,
    })
  }

  /** Delete a bucket and its git repo. */

  deleteBucket(slug) {
    return this._fetch(TyprAPI._bucketPath(slug), { method: 'DELETE' })
  }

  /** Update a bucket's metadata (description, access rules). */

  updateBucket(slug, data) {
    return this._json('PUT', TyprAPI._bucketPath(slug), data)
  }

  // ── Files ──

  /** List all files in a bucket. */

  listFiles(slug) {
    return this._fetch(`${TyprAPI._bucketPath(slug)}/files`)
  }

  /** Read a file's content. */

  readFile(slug, path) {
    return this._fetch(`${TyprAPI._bucketPath(slug)}/files/${path}`)
  }

  /** Save (overwrite) a file's content. */

  saveFile(slug, path, content) {
    return this._json(
      'PUT', `${TyprAPI._bucketPath(slug)}/files/${path}`, { content },
    )
  }

  /** Create a new file. Fails if it already exists. */

  createFile(slug, path, content) {
    return this._json(
      'POST', `${TyprAPI._bucketPath(slug)}/files`, { content: content || '', path },
    )
  }

  /** Upload files via multipart form data. */

  uploadFiles(slug, fileList, prefix) {
    const form = new FormData()
    for (const file of fileList)
      form.append('files', file)
    const qp = prefix ? `?prefix=${encodeURIComponent(prefix)}` : ''
    return this._fetch(
      `${TyprAPI._bucketPath(slug)}/files/upload${qp}`,
      { body: form, method: 'POST' },
    )
  }

  /** Delete a file from the bucket. */

  deleteFile(slug, path) {
    return this._fetch(
      `${TyprAPI._bucketPath(slug)}/files/${path}`, { method: 'DELETE' },
    )
  }

  /** Delete a directory and all its contents. */

  deleteDir(slug, path) {
    return this._fetch(
      `${TyprAPI._bucketPath(slug)}/files/dir/${path}`,
      { method: 'DELETE' },
    )
  }

  /** Rename/move a directory. */

  renameDir(slug, oldPath, newPath) {
    const path = `${TyprAPI._bucketPath(slug)}/files/rename-dir`
    return this._json(
      'POST', path, { new_path: newPath, old_path: oldPath },
    )
  }

  // ── Git ──

  /** Get working tree status. */

  gitStatus(slug) {
    return this._fetch(`${TyprAPI._bucketPath(slug)}/git/status`)
  }

  /** Stage files and create a commit. */

  gitCommit(slug, files, message) {
    return this._json(
      'POST', `${TyprAPI._bucketPath(slug)}/git/commit`, { files, message },
    )
  }

  /** Get commit history, optionally filtered by path. */

  gitLog(slug, path, limit) {
    let url = `${TyprAPI._bucketPath(slug)}/git/log`
    const params = new URLSearchParams()
    if (path)
      params.set('path', path)
    if (limit)
      params.set('max_count', limit)
    if (params.size)
      url += `?${params}`
    return this._fetch(url)
  }

  /** Get unified diffs for modified files. */

  gitDiff(slug, path) {
    let url = `${TyprAPI._bucketPath(slug)}/git/diff`
    if (path)
      url += `?path=${encodeURIComponent(path)}`
    return this._fetch(url)
  }

  /** List all file paths at a specific commit. */

  gitTree(slug, ref) {
    return this._fetch(
      `${TyprAPI._bucketPath(slug)}/git/tree/${encodeURIComponent(ref)}`,
    )
  }

  /** Retrieve a file's content at a specific commit. */

  gitShow(slug, ref, path) {
    const rev = encodeURIComponent(ref)
    return this._fetch(
      `${TyprAPI._bucketPath(slug)}/git/show/${rev}/${path}`,
    )
  }

  /** Restore files from a specific commit into the working tree. */

  gitRestore(slug, ref, paths) {
    return this._json(
      'POST', `${TyprAPI._bucketPath(slug)}/git/restore`, { paths, ref },
    )
  }

  // ── Compile ──

  /** Compile a .typ file to SVG. */

  compile(slug, path) {
    return this._fetch(`${TyprAPI._bucketPath(slug)}/compile/svg/${path}`)
  }

  // ── Templates ──

  /** Fetch available Typst templates from the public index. */

  listTemplates() {
    return this._fetch('/api/templates')
  }

  /** Fetch templates from the local package directory. */

  listLocalTemplates() {
    return this._fetch('/api/templates/local')
  }

  /** Initialize a bucket from a Typst template. */

  initTemplate(slug, name, version, namespace) {
    const path = `${TyprAPI._bucketPath(slug)}/init-template`
    return this._json('POST', path, { name, namespace: namespace || 'preview', version })
  }

}
