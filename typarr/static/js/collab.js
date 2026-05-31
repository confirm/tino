import {
  Doc,
  WebsocketProvider,
  keymap,
  yCollab,
  yUndoManagerKeymap,
} from './vendor/codemirror.js'
import { SINGLE_ITEM } from './constants.js'

/**
 * Manages a single Yjs collaboration session for one file.
 *
 * The CodeMirror view is bound to the room's YText through y-codemirror.next
 * (yCollab), which handles bidirectional sync, remote cursors, and undo. This
 * class owns the surrounding lifecycle that yCollab does not: the WebSocket
 * provider, the drop/reconnect latch, and replaying offline edits after a
 * server restart rebuilds the room.
 */

export class CollabSession {

  /**
   * @param {string} slug - Bucket identifier.
   * @param {string} path - File path within the bucket.
   * @param {CodeMirrorEditor} editor - Editor shim wrapping the CM view.
   * @param {Function} onStatusCb - Lifecycle callback ('synced' | 'dropped').
   * @param {object} [opts] - Options.
   * @param {boolean} [opts.preserveLocal] - On the first sync, replay the local
   *   buffer onto the server content instead of adopting it. Set when rebuilding
   *   after a drop so edits made while offline survive.
   * @param {object} [opts.user] - Awareness user ({ name, color }) for the
   *   remote-cursor label shown to other collaborators.
   */

  constructor(slug, path, editor, onStatusCb, opts = {}) {
    this._slug = slug
    this._path = path
    this._editor = editor
    this._onStatusCb = onStatusCb || null
    this._preserveLocal = opts.preserveLocal || false
    this._user = opts.user || null
    this._resetState()
  }

  /** Open the WebSocket connection and start syncing. */

  connect() {
    this._doc = new Doc()
    this._ytext = this._doc.getText('content')
    const wsUrl = CollabSession._buildWsUrl(this._slug)
    this._provider = new WebsocketProvider(wsUrl, this._path, this._doc)
    if (this._user)
      this._provider.awareness.setLocalStateField('user', this._user)
    this._provider.on('sync', synced => this._onSync(synced))
    this._provider.on('status', evt => this._onProviderStatus(evt.status))
  }

  /** @returns {boolean} True if connected and initial sync is done. */

  isConnected() {
    return this._synced && this._provider !== null
  }

  /** Tear down the provider, doc, and editor binding. */

  disconnect() {
    this._closing = true
    this._editor.setCollab(null)
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

  /**
   * Adopt the room content and bind yCollab on the FIRST sync, not at connect
   * time. yCollab's sync plugin assumes the editor and the YText already match
   * and only forwards incremental edits — it never seeds one from the other. So
   * the buffer is explicitly set to the synced YText before binding; doing this
   * any earlier (while the YText is still empty) would blank the editor, or
   * leave it stuck empty if the server were still down. Capturing the buffer
   * first lets offline edits be reconciled on top once real content has arrived.
   */

  _onSync(synced) {
    this._synced = synced
    if (!synced || this._bound || !this._ytext)
      return
    const local = this._editor.content
    this._editor.setContent(this._ytext.toString())
    this._bindCollab()
    if (this._preserveLocal)
      this._reconcile(local)
    this._preserveLocal = false
    if (this._editor.content !== local)
      this._editor.signalChange()
    if (this._onStatusCb)
      this._onStatusCb('synced')
  }

  _bindCollab() {
    this._bound = true
    this._editor.setCollab([
      yCollab(this._ytext, this._provider.awareness),
      keymap.of(yUndoManagerKeymap),
    ])
  }

  /**
   * Reconnect reconciliation: the buffer was just replaced with the room's
   * freshly synced content, so the local snapshot (captured before the adopt,
   * including offline edits) is newer. Replay the difference as a single editor
   * transaction — yCollab's sync plugin propagates it upstream as an incremental
   * edit, which avoids re-inserting the whole document (the cause of past
   * duplication).
   * @param {string} local - The buffer captured immediately before the adopt.
   */

  _reconcile(local) {
    const server = this._editor.content
    if (local === server)
      return
    const delta = CollabSession._diffValues(server, local)
    this._editor.view.dispatch({
      changes: {
        from: delta.start,
        insert: delta.inserted,
        to: delta.start + delta.deleteCount,
      },
    })
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

  _resetState() {
    this._doc = null
    this._ytext = null
    this._provider = null
    this._synced = false
    this._bound = false
    this._wasConnected = false
    this._closing = false
  }

}
