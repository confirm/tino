import { CollabSession } from './collab.js'

/* Remote-cursor color: a hue hashed from the username, with fixed saturation
 * and lightness so every user gets a distinct but uniformly readable color. */

const HUE_STEPS = 360

const HASH_PRIME = 31

const CURSOR_SATURATION = 50

const CURSOR_LIGHTNESS = 50

/**
 * Manages the collaborative editing session lifecycle.
 * Wraps CollabSession with connect/disconnect and reconnect handling.
 */

export class EditorCollab {

  /** @param {TinoApp} app - Main application instance. */

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
    const isText = !this.app.els.editor.hidden
    if (!path || !canEdit || !isText)
      return
    this._session = new CollabSession(
      this.app.bucket,
      path,
      this.app.els.editor,
      ev => this._onEvent(ev),
      { preserveLocal: reconnect, user: this._awarenessUser() },
    )
    this._session.connect()
  }

  /** Build the awareness user (name + stable color) for remote cursors. */

  _awarenessUser() {
    const name = this.app.username || 'anonymous'
    return { color: EditorCollab._colorFor(name), name }
  }

  /**
   * Derive a stable, vivid cursor color from a username. The name is hashed to
   * a hue (multiply-accumulate over its code points); saturation and lightness
   * are held constant so the result is always readable, on light or dark.
   */

  static _colorFor(name) {
    let hue = 0
    for (const ch of name)
      hue = (hue * HASH_PRIME + ch.codePointAt(0)) % HUE_STEPS
    return `hsl(${hue}, ${CURSOR_SATURATION}%, ${CURSOR_LIGHTNESS}%)`
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
