import { INDEX_NOT_FOUND, SINGLE_ITEM } from './constants.js'

/** Sentinel indicating "no match result yet — keep walking". */

const NO_MATCH = Symbol('no-match')

/**
 * Builds a nested tree structure from a flat file listing and git statuses.
 * Pure data transformation — no DOM interaction.
 */

export class TreeBuilder {

  /**
   * Build a sorted tree from API file entries and git statuses.
   * @param {Array<{path: string, type: string}>} files - Flat file listing.
   * @param {Object<string, string>} gitStatuses - Map of path to git status.
   * @param {boolean} canEdit - Whether the user has edit permissions.
   * @returns {Array} Sorted array of root-level tree nodes.
   */

  static build(files, gitStatuses, canEdit) {
    const root = []
    TreeBuilder._insertApiEntries(root, files)
    TreeBuilder._insertGitOnlyFiles(root, gitStatuses, canEdit)
    TreeBuilder._sortNodes(root)
    return root
  }

  static _insertApiEntries(root, files) {
    files.forEach(file => {
      const node = TreeBuilder._makeNode(file.path, file.type)
      TreeBuilder._insertAtPath(root, file.path, node)
    })
  }

  static _insertGitOnlyFiles(root, gitStatuses, canEdit) {
    if (!canEdit)
      return
    Object.keys(gitStatuses).forEach(filePath => {
      const status = gitStatuses[filePath]
      if (status !== 'untracked' && status !== 'deleted')
        return
      if (TreeBuilder._findNode(root, filePath))
        return
      const node = TreeBuilder._makeNode(filePath, 'file')
      node.status = status
      TreeBuilder._insertAtPath(root, filePath, node)
    })
  }

  static _makeNode(filePath, type) {
    const parts = filePath.split('/')
    const last = parts.length - SINGLE_ITEM
    return {
      children: type === 'directory' ? [] : null,
      name: parts[last],
      path: filePath,
      status: null,
      type,
    }
  }

  static _insertAtPath(root, filePath, node) {
    const parts = filePath.split('/')
    if (parts.length === SINGLE_ITEM) {
      const existing = root.find(nd => nd.path === filePath)
      if (!existing)
        root.push(node)
      return
    }
    const parent = TreeBuilder._ensureParents(root, parts)
    const existing = parent.find(nd => nd.path === filePath)
    if (!existing)
      parent.push(node)
  }

  static _ensureParents(root, parts) {
    let current = root
    const depth = parts.length - SINGLE_ITEM
    for (let ix = 0; ix < depth; ix += SINGLE_ITEM) {
      const dirPath = parts.slice(0, ix + SINGLE_ITEM).join('/')
      let dir = current.find(nd => nd.path === dirPath)
      if (!dir) {
        dir = TreeBuilder._makeNode(dirPath, 'directory')
        current.push(dir)
      }
      current = dir.children
    }
    return current
  }

  static _findNode(root, filePath) {
    const parts = filePath.split('/')
    let current = root
    const last = parts.length - SINGLE_ITEM
    for (let ix = 0; ix < parts.length; ix += SINGLE_ITEM) {
      const result = TreeBuilder._matchSegment(
        current, parts, ix, last,
      )
      if (result !== NO_MATCH)
        return result
      current = current.find(
        nd => nd.path === parts.slice(0, ix + SINGLE_ITEM).join('/'),
      ).children
    }
    return null
  }

  static _matchSegment(current, parts, ix, last) {
    const segPath = parts.slice(0, ix + SINGLE_ITEM).join('/')
    const found = current.find(nd => nd.path === segPath)
    if (!found)
      return null
    if (ix === last)
      return found
    if (!found.children)
      return null
    return NO_MATCH
  }

  static _sortNodes(nodes) {
    nodes.sort((nodeA, nodeB) => {
      if (nodeA.type !== nodeB.type)
        return nodeA.type === 'directory' ? INDEX_NOT_FOUND : SINGLE_ITEM
      return nodeA.name.localeCompare(nodeB.name)
    })
    nodes.forEach(node => {
      if (node.children)
        TreeBuilder._sortNodes(node.children)
    })
  }

}
