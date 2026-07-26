export const el = function el(tag, className, text = null) {
  const node = document.createElement(tag)
  if (className)
    node.className = className
  if (text !== null)
    node.textContent = text
  return node
}

const formatWhen = value => value ? new Date(value).toLocaleString() : ''

const messageNode = function messageNode(message) {
  const node = el('div', 'review-message')
  const meta = el(
    'div', 'review-message-meta', `${message.author} · ${formatWhen(message.created_at)}`,
  )
  node.append(meta, el('div', 'review-message-body', message.body))
  return node
}

const anchorButton = function anchorButton(thread) {
  const text = `${thread.path}:${thread.anchor.line}:${thread.anchor.column}`
  const button = el('button', 'review-anchor', text)
  button.type = 'button'
  button.dataset.reviewAction = 'jump'
  return button
}

const threadActions = function threadActions(thread, openStatus) {
  const node = el('div', 'review-actions')
  const label = thread.status === openStatus ? 'Resolve' : 'Reopen'
  const action = thread.status === openStatus ? 'resolve' : 'reopen'
  const button = el('button', 'review-action-btn', label)
  button.type = 'button'
  button.dataset.reviewAction = action
  node.appendChild(button)
  return node
}

const threadHeader = function threadHeader(thread, canEdit, openStatus) {
  const header = el('div', 'review-thread-header')
  header.append(anchorButton(thread), el('span', 'review-status', thread.status))
  if (canEdit)
    header.appendChild(threadActions(thread, openStatus))
  return header
}

const messagesNode = function messagesNode(thread) {
  const messages = el('div', 'review-messages')
  for (const message of thread.messages)
    messages.appendChild(messageNode(message))
  return messages
}

const replyNode = function replyNode() {
  const reply = el('div', 'review-reply')
  const input = el('textarea', 'form-input review-reply-input')
  const button = el('button', 'btn btn-secondary btn-small review-reply-button', 'Reply')
  input.rows = 2
  input.placeholder = 'Reply...'
  button.type = 'button'
  button.dataset.reviewAction = 'reply'
  reply.append(input, button)
  return reply
}

export const reviewThreadNode = function reviewThreadNode(thread, canEdit, openStatus) {
  const item = el('li', `review-thread review-${thread.status}`)
  item.dataset.thread = thread.id
  item.appendChild(threadHeader(thread, canEdit, openStatus))
  if (thread.anchor.quote)
    item.appendChild(el('blockquote', 'review-quote', thread.anchor.quote))
  item.appendChild(messagesNode(thread))
  if (canEdit && thread.status === openStatus)
    item.appendChild(replyNode())
  return item
}
