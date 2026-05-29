import { CollabSession } from './collab.js'

/**
 * Manages the collaborative editing session lifecycle.
 * Wraps CollabSession with connect/disconnect and reconnect handling.
 */

export class EditorCollab {

  /** @param {TyparrApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._session = null
    this._reconnecting = false
  }

  /**
   * Open a collab session for the given file path.
   * @param {string} path - File path to open.
   * @param {boolean} [reconnect] - True when rebuilding after a drop: the
   *   local textarea (including offline edits) is preserved and reconciled
   *   onto the freshly synced server content. False on initial open, where
   *   the server's content is adopted as the source of truth.
   */

  connect(path, reconnect = false) {
    this.disconnect()
    this._reconnecting = reconnect
    const role = this.app.bucketRole
    const canEdit = role === 'editor' || role === 'committer'
    const isText =
      !this.app.els.editor.classList.contains('hidden')
    if (!path || !canEdit || !isText)
      return
    this._session = new CollabSession(
      this.app.bucket,
      path,
      this.app.els.editor,
      ev => this._onEvent(ev),
      { preserveLocal: reconnect },
    )
    this._session.connect()
  }

  /** Tear down the current collab session. */

  disconnect() {
    if (this._session) {
      this._session.disconnect()
      this._session = null
    }
  }

  _onEvent(event) {
    if (event === 'dropped')
      this._rebuild()
    else if (event === 'synced' && this._reconnecting) {
      this._reconnecting = false
      this.app.toast.success('Collaboration reconnected')
    }
  }

  _rebuild() {
    /*
     * The live connection dropped — typically a server restart. Rebuild on a
     * fresh, empty Y.Doc rather than letting the stale Doc auto-reconnect: a
     * restarted server re-seeds the room from disk as a NEW CRDT lineage, and
     * syncing our old lineage into it merges two independent inserts of the
     * same text, duplicating the whole file. An empty Doc re-syncs cleanly
     * from whatever the room now holds.
     *
     * Deferred so we tear the old provider down outside its own status-event
     * callback, and before its (~100ms) auto-reconnect can run the merge.
     * disconnect() sets shouldConnect=false on the old provider, so its
     * pending reconnect no-ops.
     */

    this.app.toast.error('Collaboration lost, reconnecting...')
    setTimeout(() => this.connect(this.app.currentFile, true), 0)
  }

}
