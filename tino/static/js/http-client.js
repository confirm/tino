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
      throw new Error(await HttpClient._parseError(res))
    if (res.status === HTTP_NO_CONTENT)
      return null
    return res.json()
  }

  static async _parseError(res) {
    const body = await res.text()
    try {
      return JSON.parse(body).detail || body
    }
    catch {
      return body
    }
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
