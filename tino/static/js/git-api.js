import { HttpClient } from './http-client.js'

/** Encoded bucket API base path. Shared by the API client classes. */

export const bucketPath = slug =>
  `/api/buckets/${encodeURIComponent(slug)}`

/**
 * Git endpoints of the TINO REST API.
 * Split from TinoAPI (see api.js), which extends this class, so that neither
 * file outgrows the line budget. Inherited methods stay on the same instance,
 * so callers still use ``api.gitStatus(...)`` etc.
 */

export class GitAPI extends HttpClient {

  /** Get working tree status. */

  gitStatus(slug) {
    return this._fetch(`${bucketPath(slug)}/git/status`)
  }

  /** Stage files and create a commit. */

  gitCommit(slug, files, message) {
    return this._json(
      'POST', `${bucketPath(slug)}/git/commit`, { files, message },
    )
  }

  /** Get commit history, optionally filtered by path. */

  gitLog(slug, path, limit) {
    let url = `${bucketPath(slug)}/git/log`
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
    return this._fetch(`${bucketPath(slug)}/git/diff${qs}`)
  }

  /** List all file paths at a specific commit. */

  gitTree(slug, ref) {
    return this._fetch(
      `${bucketPath(slug)}/git/tree/${encodeURIComponent(ref)}`,
    )
  }

  /** Retrieve a file's content at a specific commit. */

  gitShow(slug, ref, path) {
    const rev = encodeURIComponent(ref)
    return this._fetch(
      `${bucketPath(slug)}/git/show/${rev}/content/${path}`,
    )
  }

  /** Restore files from a specific commit into the working tree. */

  gitRestore(slug, ref, paths) {
    return this._json(
      'POST', `${bucketPath(slug)}/git/restore`, { paths, ref },
    )
  }

}
