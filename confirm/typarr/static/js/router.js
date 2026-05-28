import { INDEX_NOT_FOUND, SINGLE_ITEM } from './constants.js'

const HASH_PREFIX = '#/'

/**
 * Hash-based routing for deep-linking to buckets and files.
 * URL format: /#/{slug} or /#/{slug}/{file-path}
 */

/** Parse the current URL hash into a route object. */

export const readRoute = () => {
  const { hash } = location
  if (!hash.startsWith(HASH_PREFIX))
    return { path: null, slug: null }
  const rest = hash.slice(HASH_PREFIX.length)
  const idx = rest.indexOf('/')
  if (idx === INDEX_NOT_FOUND)
    return { path: null, slug: decodeURIComponent(rest) }
  return {
    path: decodeURIComponent(rest.slice(idx + SINGLE_ITEM)),
    slug: decodeURIComponent(rest.slice(0, idx)),
  }
}

/** Update the URL hash to reflect the current bucket and file. */

export const writeRoute = (slug, path) => {
  if (!slug) {
    history.replaceState(null, '', location.pathname)
    return
  }
  const encoded = encodeURIComponent(slug)
  if (!path) {
    history.replaceState(null, '', `${HASH_PREFIX}${encoded}`)
    return
  }
  const safePath = path.split('/').map(encodeURIComponent).join('/')
  history.replaceState(null, '', `${HASH_PREFIX}${encoded}/${safePath}`)
}
