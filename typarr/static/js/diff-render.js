import { escapeHtml } from './constants.js'

/**
 * Render a unified-diff text as an HTML string with per-line classification.
 * Each line is wrapped in a span tagged by kind: file-header, hunk, add, del,
 * context. Output lives inside <pre class="diff-block">.
 */

const FILE_HEADER_PREFIXES = [
  'diff --git',
  'index ',
  '--- ',
  '+++ ',
  'new file',
  'deleted file',
  'rename ',
  'similarity ',
  'Binary files',
]

const classify = line => {
  if (!line)
    return 'context'
  if (line.startsWith('@@'))
    return 'hunk'
  if (FILE_HEADER_PREFIXES.some(prefix => line.startsWith(prefix)))
    return 'file-header'
  if (line.startsWith('+'))
    return 'add'
  if (line.startsWith('-'))
    return 'del'
  return 'context'
}

const renderEntry = entry => {
  const header = `<div class="diff-file-path">${escapeHtml(entry.path)}</div>`
  const body = entry.diff
    .split('\n')
    .map(line => {
      const cls = `diff-line diff-${classify(line)}`
      return `<span class="${cls}">${escapeHtml(line) || ' '}</span>`
    })
    .join('')
  return `${header}<pre class="diff-block">${body}</pre>`
}

/**
 * @param {Array<{path: string, diff: string}>} entries - DiffEntry list.
 * @returns {string} HTML for a diff view. Empty diffs render as a "No changes"
 *   placeholder so callers don't need to special-case.
 */

export const renderDiffEntries = entries => {
  if (!entries || entries.length === 0)
    return '<p class="preview-empty">No changes to show.</p>'
  return entries.map(renderEntry).join('')
}
