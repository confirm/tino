/**
 * Persists open editor tabs to localStorage, keyed by bucket slug.
 */

const PREFIX = 'typr:tabs:'

const parseTabs = raw => {
  try {
    return raw ? JSON.parse(raw) : []
  }
  catch {
    return []
  }
}

/** Save the current open tabs for a bucket. */

export const persistTabs = (slug, tabs) => {
  localStorage.setItem(`${PREFIX}${slug}`, JSON.stringify(tabs))
}

/** Load saved tabs for a bucket, filtered to paths that still exist. */

export const loadSavedTabs = (slug, existingPaths) => {
  const raw = localStorage.getItem(`${PREFIX}${slug}`)
  const saved = parseTabs(raw)
  return saved.filter(tp => existingPaths.has(tp))
}
