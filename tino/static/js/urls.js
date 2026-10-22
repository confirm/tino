/**
 * URL helpers. The frontend uses relative URLs throughout (e.g. `api/me`), so
 * they resolve below whatever path TINO is served under (`/` or a sub-path
 * like `/tino/`). WebSockets need an absolute ws(s):// URL, built here.
 */

/**
 * Build an absolute WebSocket URL for an app-relative path.
 * @param {string} path - Relative path, e.g. `api/buckets/demo/events`.
 * @returns {string} The ws:// or wss:// URL below the page's base path.
 */

export const wsUrl = path => {
  const url = new URL(path, document.baseURI)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.href
}
