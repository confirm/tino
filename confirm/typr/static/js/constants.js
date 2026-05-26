export const HTTP_NO_CONTENT = 204
export const HTTP_UNAUTHORIZED = 401
export const DEBOUNCE_MS = 1000
export const TAB_SPACES = 2
export const ZOOM_STEP = 10
export const ZOOM_MIN = 50
export const ZOOM_MAX = 200
export const PANEL_MIN_WIDTH = 120
export const PANEL_MAX_WIDTH = 500
export const INDEX_NOT_FOUND = -1
export const SINGLE_ITEM = 1
export const ISO_DATETIME_LEN = 19
export const SHA_SHORT_LEN = 7

export const FILE_ICON =
  '<span class="material-symbols-outlined file-icon">' +
  'description</span>'

export const FOLDER_ICON =
  '<span class="material-symbols-outlined folder-icon">' +
  'folder</span>'

export const TOGGLE_ICON =
  '<span class="material-symbols-outlined folder-toggle">' +
  'expand_more</span>'

export const STATUS_ICONS = {
  deleted: 'close',
  modified: 'edit',
  untracked: 'add',
}

export const escapeHtml = str =>
  str.replace(/&/gu, '&amp;').replace(/</gu, '&lt;').replace(/>/gu, '&gt;')

export const STATUS_CLASSES = {
  deleted: 'status-deleted',
  modified: 'status-modified',
  untracked: 'status-untracked',
}
