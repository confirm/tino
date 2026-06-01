import {
  HighlightStyle,
  LanguageSupport,
  foldService,
  indentService,
  syntaxHighlighting,
  tags,
} from './vendor/codemirror.js'
import { INDEX_NOT_FOUND, SINGLE_ITEM } from './constants.js'
import { typstLanguage } from './codemirror-typst-tokens.js'

/**
 * Typst language extensions: syntax highlighting, structural indent,
 * bracket-based folding. The token grammar lives in codemirror-typst-tokens.
 */

const OPENERS = '{[('
const CLOSERS = '}])'
const MATCH = { '(': ')', '[': ']', '{': '}' }
const MAX_FOLD_SCAN = 200000

const typstHighlight = HighlightStyle.define([
  { class: 'cm-typst-comment', tag: tags.lineComment },
  { class: 'cm-typst-comment', tag: tags.blockComment },
  { class: 'cm-typst-string', tag: tags.string },
  { class: 'cm-typst-string', tag: tags.monospace },
  { class: 'cm-typst-keyword', tag: tags.keyword },
  { class: 'cm-typst-function', tag: tags.function(tags.variableName) },
  { class: 'cm-typst-variable', tag: tags.variableName },
  { class: 'cm-typst-number', tag: tags.number },
  { class: 'cm-typst-heading', tag: tags.heading },
  { class: 'cm-typst-strong', tag: tags.strong },
  { class: 'cm-typst-emphasis', tag: tags.emphasis },
  { class: 'cm-typst-meta', tag: tags.meta },
  { class: 'cm-typst-label', tag: tags.labelName },
  { class: 'cm-typst-link', tag: tags.link },
  { class: 'cm-typst-punct', tag: tags.punctuation },
])

const _firstChar = text => (/^\s*(?<ch>\S)/u.exec(text) || { groups: {} }).groups.ch || ''

const _stripComments = text =>
  text.replace(/\/\/.*$/u, '').replace(/\/\*.*?\*\//gu, '').trimEnd()

const _computeIndent = (prevIndent, lastCh, firstCh, unit) => {
  let indent = prevIndent
  if (lastCh && OPENERS.includes(lastCh))
    indent += unit
  if (firstCh && CLOSERS.includes(firstCh))
    indent = Math.max(0, indent - unit)
  return indent
}

/**
 * Walk backward from `pos` to the nearest non-blank line. Uses the indent
 * context's break-aware lineAt (bias -1) so that, when Enter simulates a
 * line break, this sees the line being left rather than the new empty one.
 * Returns null when only blank lines precede `pos`.
 */

const _prevNonBlank = (context, pos) => {
  if (pos < 0)
    return null
  let line = context.lineAt(pos, INDEX_NOT_FOUND)
  while (line.text.trim() === '' && line.from > 0)
    line = context.lineAt(line.from - SINGLE_ITEM, INDEX_NOT_FOUND)
  return line.text.trim() === '' ? null : line
}

/**
 * Typst-aware indent: inherit the previous non-blank line's indentation, add
 * one unit when that line ends with an opener ({ [ () and subtract one unit
 * when the line being indented starts with a closer (} ] )). Trailing
 * comments are stripped so `foo( // note` still counts as an opener. Plain
 * prose keeps the surrounding indent instead of drifting line to line.
 */

const _typstIndent = indentService.of((context, pos) => {
  const { unit } = context
  const cur = context.lineAt(pos, SINGLE_ITEM)
  const ref = _prevNonBlank(context, cur.from - SINGLE_ITEM)
  if (ref === null)
    return 0
  const base = /^[ \t]*/u.exec(ref.text)[0].length
  const lastCh = _stripComments(ref.text).slice(INDEX_NOT_FOUND)
  return _computeIndent(base, lastCh, _firstChar(cur.text), unit)
})

/**
 * Fold ranges for `{...}` and `[...]` blocks that open at end-of-line.
 * Scans forward from the opener while tracking nesting depth; bounded by a
 * MAX_FOLD_SCAN guard so pathological inputs don't stall.
 */

const _findFoldEnd = (state, openPos, open) => {
  const close = MATCH[open]
  const limit = Math.min(state.doc.length, openPos + MAX_FOLD_SCAN)
  let depth = SINGLE_ITEM
  for (let pos = openPos + SINGLE_ITEM; pos < limit; pos += SINGLE_ITEM) {
    const ch = state.doc.sliceString(pos, pos + SINGLE_ITEM)
    if (ch === open)
      depth += SINGLE_ITEM
    else if (ch === close) {
      depth -= SINGLE_ITEM
      if (depth === 0)
        return pos
    }
  }
  return INDEX_NOT_FOUND
}

const _typstFold = foldService.of((state, lineStart, lineEnd) => {
  const text = state.doc.sliceString(lineStart, lineEnd)
  const match = /[{[]\s*$/u.exec(text)
  if (!match)
    return null
  const openPos = lineStart + match.index
  const open = text[match.index]
  const closePos = _findFoldEnd(state, openPos, open)
  if (closePos === INDEX_NOT_FOUND)
    return null
  return { from: lineEnd, to: closePos }
})

const LIST_RE = /^(?<indent>[ \t]*)(?<bullet>[-+]|\d+\.)[ \t]+(?<body>.*)$/u

const _nextMarker = bullet => {
  if (bullet === '-' || bullet === '+')
    return bullet
  return `${Number(bullet.slice(0, INDEX_NOT_FOUND)) + SINGLE_ITEM}.`
}

const _applyListEnter = (view, line, head, groups) => {
  const { body, bullet, indent } = groups
  if (body.trim() === '') {
    view.dispatch({
      changes: { from: line.from, insert: '', to: line.to },
      selection: { anchor: line.from },
    })
    return true
  }
  const insert = `\n${indent}${_nextMarker(bullet)} `
  view.dispatch({
    changes: { from: head, insert },
    scrollIntoView: true,
    selection: { anchor: head + insert.length },
  })
  return true
}

/**
 * Continue a Typst list when Enter is pressed on a list item: repeat the
 * marker, incrementing numbered markers (1. -> 2.). Pressing Enter on an
 * empty item clears the marker and ends the list. Returns false for non-list
 * lines so the default newline-and-indent handler runs instead.
 */

const _listEnter = view => {
  const range = view.state.selection.main
  if (!range.empty)
    return false
  const line = view.state.doc.lineAt(range.head)
  const match = LIST_RE.exec(line.text)
  if (match === null)
    return false
  return _applyListEnter(view, line, range.head, match.groups)
}

/** Keymap entries for Typst-specific editing (list continuation). */

export const typstKeymap = [{ key: 'Enter', run: _listEnter }]

/** Build the Typst language support extension. */

export const typst = () => [
  new LanguageSupport(typstLanguage),
  syntaxHighlighting(typstHighlight),
  _typstIndent,
  _typstFold,
]
