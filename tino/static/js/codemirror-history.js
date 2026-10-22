import {
  Compartment,
  EditorState,
  Transaction,
  history,
  historyKeymap,
  keymap,
  ySyncAnnotation,
} from './vendor/codemirror.js'

/**
 * Undo history for the shared editor. The one EditorView is reused for every
 * file and bucket, so the history must be reset whenever a document is loaded,
 * and must only ever contain the local user's edits.
 */

const _compartment = new Compartment()

/** Undo/redo history — always active, so Vim's `u`, Ctrl-r and Ctrl-Z agree. */

const _historyExt = () => [history(), keymap.of(historyKeymap)]

/**
 * Keep collaborators' edits out of the local undo history. yCollab applies
 * remote changes as ordinary transactions tagged with ySyncAnnotation, so
 * without this Ctrl-Z would revert other people's typing. The history still
 * maps local undo steps over them.
 */

const _remoteEditsNotUndoable = () => EditorState.transactionExtender.of(tr => {
  if (!tr.annotation(ySyncAnnotation))
    return null
  return { annotations: Transaction.addToHistory.of(false) }
})

/** @returns {Array} The resettable undo history extensions. */

export const undoHistory = () => [_compartment.of(_historyExt()), _remoteEditsNotUndoable()]

/**
 * Dispatch a transaction (typically a whole-document replacement) without
 * recording it, then start a fresh undo history. Undo must never step back into
 * the previously loaded document, which yCollab would then push into the new
 * file's room. The history field is dropped and re-added in two transactions,
 * since a field that stays in the configuration keeps its state across a
 * reconfigure.
 * @param {EditorView} view - The editor view.
 * @param {object} spec - Transaction spec to dispatch.
 */

export const dispatchWithFreshHistory = (view, spec) => {
  view.dispatch({
    ...spec,
    annotations: [...spec.annotations || [], Transaction.addToHistory.of(false)],
    effects: _compartment.reconfigure([]),
  })
  view.dispatch({ effects: _compartment.reconfigure(_historyExt()) })
}
