/**
 * Entry point for the combined editor bundle.
 *
 * Re-exports every third-party symbol the editor needs — CodeMirror, Yjs,
 * y-websocket, and the y-codemirror.next binding — so esbuild resolves the
 * bare specifiers into ONE vendored file. They must share a single bundle:
 * yCollab bridges CodeMirror and Yjs, so both frameworks have to resolve to
 * the same module instances (a second copy would break facet/type identity).
 */

export { Annotation, Compartment, EditorState } from '@codemirror/state'
export {
  EditorView,
  drawSelection,
  keymap,
  lineNumbers,
  placeholder,
} from '@codemirror/view'
export { Doc } from 'yjs'
export { WebsocketProvider } from 'y-websocket'
export { yCollab, yUndoManagerKeymap } from 'y-codemirror.next'
export {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from '@codemirror/commands'
export {
  HighlightStyle,
  LanguageSupport,
  StreamLanguage,
  bracketMatching,
  codeFolding,
  foldGutter,
  foldKeymap,
  foldService,
  indentOnInput,
  indentService,
  indentUnit,
  syntaxHighlighting,
} from '@codemirror/language'
export { gotoLine, highlightSelectionMatches, searchKeymap } from '@codemirror/search'
export { tags } from '@lezer/highlight'
