import { CollabSession } from './collab.js'

/**
 * Manages the collaborative editing session lifecycle.
 * Wraps CollabSession with connect/disconnect and reconnect handling.
 */

export class EditorCollab {

  /** @param {TyprApp} app - Main application instance. */

  constructor(app) {
    this.app = app
    this._session = null
  }

  /** Open a collab session for the given file path. */

  connect(path) {
    this.disconnect()
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
      st => this._onStatus(st),
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

  _onStatus(status) {
    if (status === 'disconnected')
      this.app.toast.error('Collaboration disconnected')
    else if (status === 'reconnected') {
      this.app.toast.success('Collaboration reconnected')

      /*
       * Recreate the session with a fresh Y.Doc on reconnect. The server
       * destroys its room when the last client disconnects and rebuilds
       * it from disk as a new CRDT insert. Reusing our old Doc would
       * merge two independent inserts of the same content, duplicating.
       */

      this.connect(this.app.currentFile)
    }
  }

}
