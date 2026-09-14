import { HTTP_NO_CONTENT, HTTP_UNAUTHORIZED } from './constants.js'

/**
 * Low-level HTTP transport for the REST API client.
 * Handles auth redirects, error parsing, and JSON-body requests.
 */

export class HttpClient {

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
    if (res.status === HTTP_UNAUTHORIZED) {
      window.location.href = '/login'
      throw new Error('Session expired')
    }
    if (!res.ok)
      throw HttpClient._error(await res.text())
    if (res.status === HTTP_NO_CONTENT)
      return null
    return res.json()
  }

  /** Build an Error, carrying `detail.diagnostics` when the body has them. */

  static _error(body) {
    let detail = body
    try {
      detail = JSON.parse(body).detail || body
    }
    catch {
      // Not JSON keep the raw body.
    }
    if (detail && typeof detail === 'object') {
      const err = new Error(detail.message || body)
      err.diagnostics = detail.diagnostics || []
      return err
    }
    return new Error(detail)
  }

  /** Send a JSON-body request (POST/PUT). */

  _json(method, path, data) {
    return this._fetch(path, {
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
      method,
    })
  }

}
