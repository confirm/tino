/* global Prism */

/**
 * Prism.js grammar for Typst markup.
 *
 * The sort-keys rule is disabled for this file: Prism evaluates
 * patterns in object-insertion order, so reordering keys
 * alphabetically would change matching precedence.
 */

/* eslint-disable sort-keys */

const KEYWORDS = [
  'and',
  'as',
  'auto',
  'break',
  'context',
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
].join('|')

Prism.languages.typst = {
  comment: [
    { greedy: true, pattern: /\/\*[\s\S]*?\*\//u },
    { greedy: true, pattern: /\/\/.*/u },
  ],
  string: { greedy: true, pattern: /"(?:\\.|[^"\\\n])*"/u },
  'raw-block': {
    alias: 'string',
    greedy: true,
    inside: {
      lang: { alias: 'attr-name', pattern: /^```\w+/u },
      punctuation: /```/u,
    },
    pattern: /```[\s\S]*?```/u,
  },
  'raw-inline': { alias: 'string', greedy: true, pattern: /`[^`\n]+`/u },
  math: { alias: 'function', greedy: true, pattern: /\$[^$]*\$/u },
  heading: { alias: 'important', pattern: /^=+[ \t].*$/mu },
  'list-marker': { alias: 'punctuation', pattern: /^[ \t]*[-+][ \t]/mu },
  'enum-marker': { alias: 'punctuation', pattern: /^[ \t]*\d+\.[ \t]/mu },
  'term-marker': { alias: 'punctuation', pattern: /^[ \t]*\/[ \t][^:\n]+:/mu },
  label: { alias: 'symbol', pattern: /<[\w.:-]+>/u },
  ref: { alias: 'symbol', pattern: /@[\w.:-]+/u },
  url: { alias: 'string', pattern: /https?:\/\/\S+/u },
  strong: {
    inside: { punctuation: /^\*|\*$/u },
    pattern: /\*[^*\n]+\*/u,
  },
  emphasis: {
    inside: { punctuation: /^_|_$/u },
    pattern: /_[^_\n]+_/u,
  },
  function: {
    alias: 'function-name',
    lookbehind: true,
    pattern: /(?<bh>#)[\w-]+(?=[([])/u,
  },
  keyword: {
    lookbehind: true,
    pattern: new RegExp(`(?<bh>#|\\b)(?:${KEYWORDS})\\b`, 'u'),
  },
  'hash-expression': { alias: 'variable', pattern: /#[\w-]+/u },
  number: { pattern: /\b\d+(?:\.\d+)?(?:pt|mm|cm|in|em|fr|deg|rad|%)?\b/u },
  escape: { alias: 'string', pattern: /\\./u },
  punctuation: /[{}[\]()<>:;,]/u,
}
