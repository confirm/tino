import { StreamLanguage, tags } from './vendor/codemirror.js'
import { SINGLE_ITEM } from './constants.js'

/**
 * Typst stream tokenizer. A regex-based per-line state machine — no real
 * parser. Stateful for multi-line constructs (block comments, raw blocks,
 * math). Token names map to Lezer highlight tags via tokenTable below.
 */

const KEYWORDS = new Set([
  'and',
  'as',
  'auto',
  'break',
  'continue',
  'else',
  'false',
  'for',
  'if',
  'import',
  'in',
  'include',
  'let',
  'none',
  'not',
  'or',
  'return',
  'set',
  'show',
  'true',
  'while',
])

const NUMBER = /\d+(?:\.\d+)?(?:em|pt|in|cm|mm|fr|deg|rad|%)?/u
const HEADING_LINE = /[=]{1,4} /u
const LIST_LINE = /\s*[-+/] /u
const LABEL = /<[a-zA-Z0-9_-]+>/u
const REF = /@[a-zA-Z][\w-]*/u
const PUNCT = /[(){}[\],;.]/u

const _startState = () => ({ mode: 'markup' })

const _inBlockComment = (stream, state) => {
  while (!stream.eol()) {
    if (stream.match('*/')) {
      state.mode = 'markup'
      return 'blockComment'
    }
    stream.next()
  }
  return 'blockComment'
}

const _inRawBlock = (stream, state) => {
  while (!stream.eol()) {
    if (stream.match('```')) {
      state.mode = 'markup'
      return 'monospace'
    }
    stream.next()
  }
  return 'monospace'
}

const _inMath = (stream, state) => {
  if (stream.eat('$')) {
    state.mode = 'markup'
    return 'meta'
  }
  while (!stream.eol() && stream.peek() !== '$')
    stream.next()
  return 'mathInner'
}

const _eatString = stream => {
  while (!stream.eol()) {
    const ch = stream.next()
    if (ch === '\\')
      stream.next()
    else if (ch === '"')
      break
  }
  return 'string'
}

const _eatInlineRaw = stream => {
  while (!stream.eol()) {
    if (stream.eat('`'))
      return 'monospace'
    stream.next()
  }
  return 'monospace'
}

const _eatWrapped = (stream, delim, tagName) => {
  while (!stream.eol()) {
    const ch = stream.next()
    if (ch === delim)
      return tagName
    if (ch === '\\')
      stream.next()
  }
  return tagName
}

const _eatHash = stream => {
  if (!stream.eatWhile(/[a-zA-Z_]/u))
    return 'meta'
  stream.eatWhile(/[\w-]/u)
  const word = stream.current().slice(SINGLE_ITEM)
  if (KEYWORDS.has(word))
    return 'keyword'
  if (stream.peek() === '(')
    return 'function'
  return 'variableName'
}

const _multiLineToken = (stream, state) => {
  if (state.mode === 'blockComment')
    return _inBlockComment(stream, state)
  if (state.mode === 'rawBlock')
    return _inRawBlock(stream, state)
  if (state.mode === 'math')
    return _inMath(stream, state)
  return null
}

const _tryComment = (stream, state) => {
  if (stream.match('//')) {
    stream.skipToEnd()
    return 'lineComment'
  }
  if (stream.match('/*')) {
    state.mode = 'blockComment'
    return _inBlockComment(stream, state)
  }
  return null
}

const _tryQuoted = (stream, state) => {
  if (stream.match('```')) {
    state.mode = 'rawBlock'
    return 'monospace'
  }
  if (stream.eat('`'))
    return _eatInlineRaw(stream)
  if (stream.eat('$')) {
    state.mode = 'math'
    return 'meta'
  }
  if (stream.eat('"'))
    return _eatString(stream)
  return null
}

const _tryLineStart = stream => {
  if (!stream.sol())
    return null
  if (stream.match(HEADING_LINE)) {
    stream.skipToEnd()
    return 'heading'
  }
  if (stream.match(LIST_LINE))
    return 'meta'
  return null
}

const _tryInlinePrefix = stream => {
  if (stream.eat('#'))
    return _eatHash(stream)
  if (stream.eat('*'))
    return _eatWrapped(stream, '*', 'strong')
  if (stream.eat('_'))
    return _eatWrapped(stream, '_', 'emphasis')
  return null
}

const _tryInlinePattern = stream => {
  if (stream.match(LABEL))
    return 'labelName'
  if (stream.match(REF))
    return 'link'
  if (stream.match(NUMBER))
    return 'number'
  if (stream.match(PUNCT))
    return 'punctuation'
  return null
}

const _tryInline = stream => {
  const prefix = _tryInlinePrefix(stream)
  if (prefix !== null)
    return prefix
  const pattern = _tryInlinePattern(stream)
  if (pattern !== null)
    return pattern
  stream.next()
  return null
}

const _markupToken = (stream, state) => {
  if (stream.eatSpace())
    return null
  return _tryComment(stream, state)
    || _tryQuoted(stream, state)
    || _tryLineStart(stream)
    || _tryInline(stream)
}

const _token = (stream, state) =>
  _multiLineToken(stream, state) || _markupToken(stream, state)

export const typstLanguage = StreamLanguage.define({
  languageData: {
    closeBrackets: { brackets: ['(', '[', '{', '"'] },
    commentTokens: { block: { close: '*/', open: '/*' }, line: '//' },
    indentOnInput: /^\s*[}\])]$/u,
  },
  name: 'typst',
  startState: _startState,
  token: _token,
  tokenTable: {
    blockComment: tags.blockComment,
    emphasis: tags.emphasis,
    function: tags.function(tags.variableName),
    heading: tags.heading,
    keyword: tags.keyword,
    labelName: tags.labelName,
    lineComment: tags.lineComment,
    link: tags.link,
    mathInner: tags.string,
    meta: tags.meta,
    monospace: tags.monospace,
    number: tags.number,
    punctuation: tags.punctuation,
    string: tags.string,
    strong: tags.strong,
    variableName: tags.variableName,
  },
})
