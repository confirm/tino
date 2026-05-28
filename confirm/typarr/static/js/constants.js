/**
 * Shared constants, icons, and utilities used across the Typarr frontend.
 */

/** HTTP status code for responses with no body. */

export const HTTP_NO_CONTENT = 204

/** HTTP status code for unauthenticated requests. */

export const HTTP_UNAUTHORIZED = 401

/** Delay in ms before auto-saving after the user stops typing. */

export const DEBOUNCE_MS = 1000

/** Number of spaces inserted when pressing Tab in the editor. */

export const TAB_SPACES = 2

/** Percentage increment for preview zoom in/out. */

export const ZOOM_STEP = 10

/** Minimum allowed preview zoom percentage. */

export const ZOOM_MIN = 50

/** Maximum allowed preview zoom percentage. */

export const ZOOM_MAX = 200

/** Minimum drag width in px for resizable panels. */

export const PANEL_MIN_WIDTH = 120

/** Maximum drag width in px for resizable panels. */

export const PANEL_MAX_WIDTH = 500

/** Sentinel returned by indexOf when an element is not found. */

export const INDEX_NOT_FOUND = -1

/** Length argument for single-item splice operations. */

export const SINGLE_ITEM = 1

/** Characters to keep when slicing an ISO timestamp (YYYY-MM-DD HH:MM:SS). */

export const ISO_DATETIME_LEN = 19

/** Number of hex characters shown for abbreviated commit SHAs. */

export const SHA_SHORT_LEN = 7

/** Material Symbols icon for a file node in the tree. */

export const FILE_ICON =
  '<span class="material-symbols-outlined file-icon">' +
  'description</span>'

/** Material Symbols icon for a folder node in the tree. */

export const FOLDER_ICON =
  '<span class="material-symbols-outlined folder-icon">' +
  'folder</span>'

/** Material Symbols expand/collapse icon for folder nodes. */

export const TOGGLE_ICON =
  '<span class="material-symbols-outlined folder-toggle">' +
  'expand_more</span>'

/** Maps git file status to its Material Symbols icon name. */

export const STATUS_ICONS = {
  deleted: 'close',
  modified: 'edit',
  untracked: 'add',
}

/** Escape &, <, > for safe insertion into HTML. */

export const escapeHtml = str =>
  str.replace(/&/gu, '&amp;').replace(/</gu, '&lt;').replace(/>/gu, '&gt;')

/** Maps git file status to its CSS badge class. */

export const STATUS_CLASSES = {
  deleted: 'status-deleted',
  modified: 'status-modified',
  untracked: 'status-untracked',
}
