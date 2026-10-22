/** Per-bucket persistence of the file tree's collapsed folder paths. */

const storageKey = bucket => `tino_collapsed_${bucket}`

/** Read the persisted collapsed paths, ignoring corrupt or blocked storage. */

export const loadCollapsedPaths = bucket => {
  try {
    const saved = localStorage.getItem(storageKey(bucket))
    return new Set(saved ? JSON.parse(saved) : [])
  }
  catch {
    return new Set()
  }
}

/** Persist the collapsed paths, ignoring blocked storage. */

export const saveCollapsedPaths = (bucket, paths) => {
  try {
    localStorage.setItem(storageKey(bucket), JSON.stringify([...paths]))
  }
  catch {
    // Storage unavailable (private mode, quota) the state is per-session then.
  }
}
