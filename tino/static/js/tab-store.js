/**
 * Persists open editor tabs to localStorage, keyed by bucket slug.
 *
 * Each entry is either a bare path string (caret at the top of the file) or an
 * object `{ path, line, col }` recording the 1-based caret position. Legacy
 * `path#line` string entries are still read, so older state loads unchanged.
 */

import { SINGLE_ITEM } from './constants.js'

const PREFIX = 'tino:tabs:'
const LEGACY_SEP = '#'

const parseStored = raw => {
  try {
    return raw ? JSON.parse(raw) : []
  }
  catch {
    return []
  }
}

/** Normalise a stored entry to `{ path, line, col }`, or null if unusable. */

const normalize = entry => {
  if (entry && typeof entry === 'object' && entry.path)
    return { col: entry.col || null, line: entry.line || null, path: entry.path }
  if (typeof entry !== 'string')
    return null
  const sep = entry.lastIndexOf(LEGACY_SEP)
  const suffix = entry.slice(sep + SINGLE_ITEM)
  if (sep > 0 && /^\d+$/u.test(suffix))
    return { col: null, line: Number(suffix), path: entry.slice(0, sep) }
  return { col: null, line: null, path: entry }
}

const encodeEntry = (path, pos) => {
  if (pos && (pos.line > SINGLE_ITEM || pos.col > SINGLE_ITEM))
    return { col: pos.col, line: pos.line, path }
  return path
}

/** Save the current open tabs (with caret positions) for a bucket. */

export const persistTabs = (slug, tabs, positions = {}) => {
  const encoded = tabs.map(path => encodeEntry(path, positions[path]))
  localStorage.setItem(`${PREFIX}${slug}`, JSON.stringify(encoded))
}

/**
 * Load saved tabs for a bucket, filtered to paths that still exist.
 * @returns {{tabs: string[], positions: Object<string, {line: number, col: number}>}}
 */

export const loadSavedTabs = (slug, existingPaths) => {
  const stored = parseStored(localStorage.getItem(`${PREFIX}${slug}`))
  const tabs = []
  const positions = {}
  stored.forEach(entry => {
    const norm = normalize(entry)
    if (!norm || !existingPaths.has(norm.path))
      return
    tabs.push(norm.path)
    if (norm.line)
      positions[norm.path] = { col: norm.col || SINGLE_ITEM, line: norm.line }
  })
  return { positions, tabs }
}
