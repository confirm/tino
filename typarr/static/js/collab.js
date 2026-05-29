import { Doc, WebsocketProvider } from './vendor/yjs.js'
import { SINGLE_ITEM } from './constants.js'

/**
 * Manages a single Yjs collaboration session for one file.
 * Binds a YText CRDT to a textarea with bidirectional sync.
 */

export class CollabSession {

  /**
   * @param {string} slug - Bucket identifier.
   * @param {string} path - File path within the bucket.
   * @param {HTMLTextAreaElement} textarea - Editor textarea element.
   * @param {Function} onStatusCb - Lifecycle callback ('synced' | 'dropped').
   * @param {object} [opts] - Options.
   * @param {boolean} [opts.preserveLocal] - On the first sync, replay the local
   *   buffer onto the server content instead of overwriting it. Set when
   *   rebuilding after a drop so edits made while offline survive.
   */

  constructor(slug, path, textarea, onStatusCb, opts = {}) {
    this._slug = slug
    this._path = path
    this._textarea = textarea
    this._onStatusCb = onStatusCb || null
    this._preserveLocal = opts.preserveLocal || false
    this._lastValue = ''
    this._resetState()
  }

  /** Open the WebSocket connection and start syncing. */

  connect() {
    this._doc = new Doc()
    this._ytext = this._doc.getText('content')
    const wsUrl = CollabSession._buildWsUrl(this._slug)
    this._provider = new WebsocketProvider(
      wsUrl, this._path, this._doc,
    )
    this._provider.on('sync', synced => this._onSync(synced))
    this._provider.on('status', evt => this._onProviderStatus(evt.status))
    this._bindTextarea()
    this._observeYtext()
  }

  /** @returns {boolean} True if connected and initial sync is done. */

  isConnected() {
    return this._synced && this._provider !== null
  }

  /** Tear down the provider, doc, and event listeners. */

  disconnect() {
    this._closing = true
    if (this._inputHandler)
      this._textarea.removeEventListener('input', this._inputHandler)
    if (this._observer && this._ytext)
      this._ytext.unobserve(this._observer)
    if (this._provider)
      this._provider.destroy()
    if (this._doc)
      this._doc.destroy()
    this._resetState()
  }

  // ── Internal ──

  static _buildWsUrl(slug) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const encoded = encodeURIComponent(slug)
    return `${proto}//${location.host}/api/buckets/${encoded}/collab`
  }

  _onSync(synced) {
    this._synced = synced
    if (!synced)
      return
    if (this._preserveLocal)
      this._reconcileLocal()
    else
      this._adoptRemote()
    this._preserveLocal = false
    if (this._onStatusCb)
      this._onStatusCb('synced')
  }

  /** Initial sync: take the room's authoritative content into the textarea. */

  _adoptRemote() {
    this._remoteUpdate = true
    this._textarea.value = this._ytext.toString()
    this._lastValue = this._textarea.value
    this._remoteUpdate = false
    this._textarea.dispatchEvent(new Event('input'))
  }

  /**
   * Reconnect sync after a drop: the room was rebuilt from disk, so the local
   * buffer (including edits made while offline) is newer than the server's.
   * Keep it and replay the difference onto the freshly synced server content
   * as ordinary incremental edits — this propagates the offline edits upstream
   * without re-inserting the whole document (which is what duplicated it).
   */

  _reconcileLocal() {
    const server = this._ytext.toString()
    const local = this._textarea.value
    this._lastValue = server
    if (local === server)
      return
    this._onLocalInput()
    this._textarea.dispatchEvent(new Event('input'))
  }

  _onProviderStatus(status) {
    /*
     * Ignore status changes once we start tearing down. destroy() closes the
     * socket, which makes the provider emit 'disconnected' synchronously — but
     * that's an intentional close (file switch, tab close, bucket reset), not
     * a dropped connection, and must not trigger a rebuild.
     *
     * Track the live connection with a dedicated latch rather than `_synced`:
     * on a real drop the provider clears its sync state (firing _onSync(false),
     * which resets `_synced`) immediately before emitting 'disconnected', so
     * `_synced` is already false here — keying off it would miss every drop.
     */

    if (this._closing)
      return
    if (status === 'connected')
      this._wasConnected = true
    else if (status === 'disconnected' && this._wasConnected) {
      this._wasConnected = false
      if (this._onStatusCb)
        this._onStatusCb('dropped')
    }
  }

  _bindTextarea() {
    this._lastValue = this._textarea.value
    this._inputHandler = () => this._onLocalInput()
    this._textarea.addEventListener('input', this._inputHandler)
  }

  _onLocalInput() {
    if (this._remoteUpdate)
      return
    const oldVal = this._lastValue
    const newVal = this._textarea.value
    this._lastValue = newVal
    if (!this._synced || oldVal === newVal)
      return
    const delta = CollabSession._diffValues(oldVal, newVal)
    this._doc.transact(() => {
      if (delta.deleteCount > 0)
        this._ytext.delete(delta.start, delta.deleteCount)
      if (delta.inserted.length > 0)
        this._ytext.insert(delta.start, delta.inserted)
    })
  }

  static _diffValues(oldVal, newVal) {
    let start = 0
    const minLen = Math.min(oldVal.length, newVal.length)
    while (start < minLen && oldVal[start] === newVal[start])
      start += SINGLE_ITEM
    let oldEnd = oldVal.length
    let newEnd = newVal.length
    while (
      oldEnd > start
      && newEnd > start
      && oldVal[oldEnd - SINGLE_ITEM]
        === newVal[newEnd - SINGLE_ITEM]
    ) {
      oldEnd -= SINGLE_ITEM
      newEnd -= SINGLE_ITEM
    }
    return {
      deleteCount: oldEnd - start,
      inserted: newVal.slice(start, newEnd),
      start,
    }
  }

  _observeYtext() {
    this._observer = event => {
      if (event.transaction.local)
        return
      this._applyRemoteDelta(event.delta)
    }
    this._ytext.observe(this._observer)
  }

  _applyRemoteDelta(delta) {
    /*
     * Ignore deltas until the initial sync completes. The first sync delivers
     * the whole document as one insert; applying it before _onSync runs would
     * corrupt the textarea — duplicating on initial load (concatenated onto
     * seed), or polluting the local buffer _reconcileLocal trusts on reconnect.
     * After _onSync, only incremental edits arrive and are safe to apply.
     */

    if (!this._synced)
      return
    this._remoteUpdate = true
    const sel = {
      end: this._textarea.selectionEnd,
      start: this._textarea.selectionStart,
    }
    const result = CollabSession._applyDelta(
      this._textarea.value, delta, sel,
    )
    this._textarea.value = result.value
    this._textarea.selectionStart = result.cursor.start
    this._textarea.selectionEnd = result.cursor.end
    this._lastValue = this._textarea.value
    this._remoteUpdate = false
    this._textarea.dispatchEvent(new Event('input'))
  }

  static _applyDelta(value, delta, cursor) {
    let pos = 0
    let newVal = ''
    for (const op of delta) {
      if (op.retain) {
        newVal += value.slice(pos, pos + op.retain)
        pos += op.retain
      }
      else if (op.insert)
        newVal += op.insert
      else if (op.delete)
        pos += op.delete
    }
    newVal += value.slice(pos)
    return {
      cursor: {
        end: CollabSession._mapCursor(delta, cursor.end),
        start: CollabSession._mapCursor(delta, cursor.start),
      },
      value: newVal,
    }
  }

  static _mapCursor(delta, cursor) {
    let oldPos = 0
    let newPos = 0
    for (const op of delta) {
      const resolved = CollabSession._resolveOp(
        op, cursor, oldPos, newPos,
      )
      if (resolved !== null)
        return resolved
      oldPos = CollabSession._nextOldPos(op, oldPos)
      newPos = CollabSession._nextNewPos(op, newPos)
    }
    return newPos + cursor - oldPos
  }

  static _resolveOp(op, cursor, oldPos, newPos) {
    if (op.retain && cursor <= oldPos + op.retain)
      return newPos + cursor - oldPos
    if (op.insert && cursor <= oldPos)
      return newPos
    if (op.delete && cursor <= oldPos + op.delete)
      return newPos
    return null
  }

  static _nextOldPos(op, pos) {
    if (op.retain)
      return pos + op.retain
    if (op.delete)
      return pos + op.delete
    return pos
  }

  static _nextNewPos(op, pos) {
    if (op.retain)
      return pos + op.retain
    if (op.insert)
      return pos + op.insert.length
    return pos
  }

  _resetState() {
    this._doc = null
    this._ytext = null
    this._provider = null
    this._synced = false
    this._remoteUpdate = false
    this._observer = null
    this._inputHandler = null
    this._wasConnected = false
    this._closing = false
  }

}
