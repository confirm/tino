const RECONNECT_MS = 3000
const REFRESH_MS = 300

/**
 * Subscribes to bucket-level file change events via WebSocket.
 * Triggers a debounced callback when any client mutates files.
 */

export class BucketEvents {

  /** @param {Function} onRefresh - Called when the file tree should be refreshed. */

  constructor(onRefresh) {
    this._onRefresh = onRefresh
    this._ws = null
    this._slug = null
    this._timer = null
  }

  /** Connect to the events WebSocket for a bucket. */

  connect(slug) {
    this.disconnect()
    this._slug = slug
    this._open()
  }

  /** Disconnect and stop reconnecting. */

  disconnect() {
    this._slug = null
    clearTimeout(this._timer)
    if (this._ws) {
      this._ws.close()
      this._ws = null
    }
  }

  // ── Internal ──

  _open() {
    if (!this._slug)
      return
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const encoded = encodeURIComponent(this._slug)
    const url =
      `${proto}//${location.host}/api/buckets/${encoded}/events`
    this._ws = new WebSocket(url)
    this._ws.onmessage = ev => this._onMessage(ev)
    this._ws.onclose = () => this._onClose()
  }

  _onMessage(ev) {
    const data = JSON.parse(ev.data)
    if (data.type === 'files-changed')
      this._scheduleRefresh()
  }

  _scheduleRefresh() {
    clearTimeout(this._timer)
    this._timer = setTimeout(
      () => this._onRefresh(), REFRESH_MS,
    )
  }

  _onClose() {
    this._ws = null
    if (this._slug)
      setTimeout(() => this._open(), RECONNECT_MS)
  }

}
