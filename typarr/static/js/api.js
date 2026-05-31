import { HttpClient } from './http-client.js'

/**
 * HTTP client for the Typarr REST API.
 * Wraps all backend endpoints (buckets, files, git, compile).
 */

export class TyparrAPI extends HttpClient {

  /** @returns {string} Encoded bucket API base path. */

  static _bucketPath(slug) {
    return `/api/buckets/${encodeURIComponent(slug)}`
  }

  config() {
    return this._fetch('/api/config')
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
    return this._fetch(TyparrAPI._bucketPath(slug))
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
    return this._fetch(TyparrAPI._bucketPath(slug), { method: 'DELETE' })
  }

  /** Update a bucket's metadata (description, access rules). */

  updateBucket(slug, data) {
    return this._json('PUT', TyparrAPI._bucketPath(slug), data)
  }

  // ── Files ──

  /** List all files in a bucket. */

  listFiles(slug) {
    return this._fetch(`${TyparrAPI._bucketPath(slug)}/files`)
  }

  /** Read a file's content. */

  readFile(slug, path) {
    return this._fetch(`${TyparrAPI._bucketPath(slug)}/files/${path}`)
  }

  /** Save (overwrite) a file's content. */

  saveFile(slug, path, content) {
    return this._json(
      'PUT', `${TyparrAPI._bucketPath(slug)}/files/${path}`, { content },
    )
  }

  /** Create a new file. Fails if it already exists. */

  createFile(slug, path, content) {
    return this._json(
      'POST', `${TyparrAPI._bucketPath(slug)}/files`, { content: content || '', path },
    )
  }

  /** Upload files via multipart form data. */

  uploadFiles(slug, fileList, prefix) {
    const form = new FormData()
    for (const file of fileList)
      form.append('files', file)
    const qp = prefix ? `?prefix=${encodeURIComponent(prefix)}` : ''
    return this._fetch(
      `${TyparrAPI._bucketPath(slug)}/files/upload${qp}`,
      { body: form, method: 'POST' },
    )
  }

  /** Delete a file from the bucket. */

  deleteFile(slug, path) {
    return this._fetch(
      `${TyparrAPI._bucketPath(slug)}/files/${path}`, { method: 'DELETE' },
    )
  }

  /** Delete a directory and all its contents. */

  deleteDir(slug, path) {
    return this._fetch(
      `${TyparrAPI._bucketPath(slug)}/files/dir/${path}`,
      { method: 'DELETE' },
    )
  }

  /** Rename/move a file. */

  renameFile(slug, oldPath, newPath) {
    const path = `${TyparrAPI._bucketPath(slug)}/files/rename`
    return this._json(
      'POST', path, { new_path: newPath, old_path: oldPath },
    )
  }

  /** Rename/move a directory. */

  renameDir(slug, oldPath, newPath) {
    const path = `${TyparrAPI._bucketPath(slug)}/files/rename-dir`
    return this._json(
      'POST', path, { new_path: newPath, old_path: oldPath },
    )
  }

  // ── Git ──

  /** Get working tree status. */

  gitStatus(slug) {
    return this._fetch(`${TyparrAPI._bucketPath(slug)}/git/status`)
  }

  /** Stage files and create a commit. */

  gitCommit(slug, files, message) {
    return this._json(
      'POST', `${TyparrAPI._bucketPath(slug)}/git/commit`, { files, message },
    )
  }

  /** Get commit history, optionally filtered by path. */

  gitLog(slug, path, limit) {
    let url = `${TyparrAPI._bucketPath(slug)}/git/log`
    const params = new URLSearchParams()
    if (path)
      params.set('path', path)
    if (limit)
      params.set('max_count', limit)
    if (params.size)
      url += `?${params}`
    return this._fetch(url)
  }

  /**
   * Get unified diffs.
   * Without ``ref`` returns working-tree diffs vs HEAD.
   * With ``ref`` returns the changes introduced by that commit.
   */

  gitDiff(slug, path, ref) {
    const params = []
    if (path)
      params.push(`path=${encodeURIComponent(path)}`)
    if (ref)
      params.push(`ref=${encodeURIComponent(ref)}`)
    const qs = params.length ? `?${params.join('&')}` : ''
    return this._fetch(`${TyparrAPI._bucketPath(slug)}/git/diff${qs}`)
  }

  /** List all file paths at a specific commit. */

  gitTree(slug, ref) {
    return this._fetch(
      `${TyparrAPI._bucketPath(slug)}/git/tree/${encodeURIComponent(ref)}`,
    )
  }

  /** Retrieve a file's content at a specific commit. */

  gitShow(slug, ref, path) {
    const rev = encodeURIComponent(ref)
    return this._fetch(
      `${TyparrAPI._bucketPath(slug)}/git/show/${rev}/content/${path}`,
    )
  }

  /** Restore files from a specific commit into the working tree. */

  gitRestore(slug, ref, paths) {
    return this._json(
      'POST', `${TyparrAPI._bucketPath(slug)}/git/restore`, { paths, ref },
    )
  }

  // ── Compile ──

  compile(slug, path) {
    return this._fetch(`${TyparrAPI._bucketPath(slug)}/compile/svg/${path}`)
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

  initTemplate(slug, name, version, namespace) {
    const path = `${TyparrAPI._bucketPath(slug)}/init-template`
    return this._json('POST', path, { name, namespace: namespace || 'preview', version })
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
