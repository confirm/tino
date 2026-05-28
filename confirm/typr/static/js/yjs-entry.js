/**
 * Entry point for the local Yjs bundle.
 *
 * Re-exports the symbols collab.js needs so esbuild can resolve the
 * bare specifiers ('yjs', 'y-websocket') into a single vendored file.
 */

export { Doc } from 'yjs'
export { WebsocketProvider } from 'y-websocket'
