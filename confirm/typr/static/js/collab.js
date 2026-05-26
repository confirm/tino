import { Doc } from 'yjs'
import { SINGLE_ITEM } from './constants.js'
import { WebsocketProvider } from 'y-websocket'

/**
 * Manages a single Yjs collaboration session for one file.
 * Binds a YText CRDT to a textarea with bidirectional sync.
 */

export class CollabSession {

  /**
   * @param {string} slug - Bucket identifier.
   * @param {string} path - File path within the bucket.
   * @param {HTMLTextAreaElement} textarea - Editor textarea element.
   */

  constructor(slug, path, textarea, onStatusCb) {
    this._slug = slug
    this._path = path
    this._textarea = textarea
    this._onStatusCb = onStatusCb || null
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
    this._remoteUpdate = true
    this._textarea.value = this._ytext.toString()
    this._lastValue = this._textarea.value
    this._remoteUpdate = false
    this._textarea.dispatchEvent(new Event('input'))
  }

  _onProviderStatus(status) {
    if (status === 'disconnected' && this._synced && !this._offline) {
      this._offline = true
      if (this._onStatusCb)
        this._onStatusCb('disconnected')
    }
    else if (status === 'connected' && this._offline) {
      this._offline = false
      if (this._onStatusCb)
        this._onStatusCb('reconnected')
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
    this._offline = false
  }

}
