import {
  Decoration,
  EditorView,
  StateEffect,
  StateField,
} from './vendor/codemirror.js'

const OPEN_STATUS = 'open'

export const setReviewDecorations = StateEffect.define()

export const reviewExtensions = StateField.define({
  create: () => Decoration.set([]),
  provide: field => EditorView.decorations.from(field),
  update(value, tr) {
    const effect = tr.effects.find(item => item.is(setReviewDecorations))
    return effect ? effect.value : value.map(tr.changes)
  },
})

const clampRange = (state, anchor) => {
  const max = state.doc.length
  const from = Math.max(0, Math.min(anchor.from_offset, max))
  const to = Math.max(from, Math.min(anchor.to_offset, max))
  return { from, to }
}

const markerFor = (state, thread) => {
  const { from, to } = clampRange(state, thread.anchor)
  if (to > from) {
    return Decoration.mark({
      attributes: { 'data-review-id': thread.id },
      class: 'cm-review-mark',
    }).range(from, to)
  }
  const line = state.doc.lineAt(from)
  return Decoration.line({
    attributes: { 'data-review-id': thread.id },
    class: 'cm-review-line',
  }).range(line.from)
}

export const buildReviewDecorations = (state, threads) => Decoration.set(
  (threads || [])
    .filter(thread => thread.status === OPEN_STATUS)
    .map(thread => markerFor(state, thread)),
  true,
)

export const setReviewThreads = (view, threads) => {
  view.dispatch({
    effects: setReviewDecorations.of(
      buildReviewDecorations(view.state, threads),
    ),
  })
}

export const selectReviewRange = (view, from, to) => {
  const max = view.state.doc.length
  const start = Math.max(0, Math.min(from, max))
  const end = Math.max(start, Math.min(to, max))
  // eslint-disable-next-line id-length -- CodeMirror's scrollIntoView axis key
  const scroll = EditorView.scrollIntoView(start, { y: 'center' })
  view.dispatch({
    effects: scroll,
    selection: { anchor: start, head: end },
  })
  view.focus()
}
