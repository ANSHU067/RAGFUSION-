import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import ReactMarkdown from 'react-markdown'
import { ChatBubble } from '../src/components/chat/ChatBubble'
import { MarkdownRenderer } from '../src/components/chat/MarkdownRenderer'

vi.mock('react-markdown', () => ({ default: vi.fn(({ children }) => <div>{children}</div>) }))
beforeEach(() => { vi.clearAllMocks() })
afterEach(cleanup)

test('existing bubbles skip Markdown work while content, citations, and actions stay current', () => {
  const copy = vi.fn()
  const message = { id: 'answer', role: 'assistant', content: 'First answer' }
  const view = render(<ChatBubble message={message} onCopy={copy} />)
  const renders = ReactMarkdown.mock.calls.length
  view.rerender(<ChatBubble message={message} onCopy={copy} />)
  expect(ReactMarkdown).toHaveBeenCalledTimes(renders)

  const withCitation = { ...message, citations: [{ source_type: 'document', source_id: 'doc', source_name: 'Guide' }] }
  view.rerender(<ChatBubble message={withCitation} onCopy={copy} />)
  expect(screen.getByText('Guide')).toBeDefined()
  expect(ReactMarkdown).toHaveBeenCalledTimes(renders)

  const newCopy = vi.fn()
  view.rerender(<ChatBubble message={{ ...withCitation, content: 'Updated answer' }} onCopy={newCopy} />)
  expect(screen.getByText('Updated answer')).toBeDefined()
  expect(ReactMarkdown).toHaveBeenCalledTimes(renders + 1)
  fireEvent.click(screen.getByRole('button', { name: 'Copy response' }))
  expect(newCopy).toHaveBeenCalledWith('Updated answer')
  expect(copy).not.toHaveBeenCalled()
})

test('Markdown memoization still updates content, class names, and custom renderers', () => {
  const view = render(<MarkdownRenderer content="Text" className="first" />)
  const renders = ReactMarkdown.mock.calls.length
  view.rerender(<MarkdownRenderer content="Text" className="first" />)
  expect(ReactMarkdown).toHaveBeenCalledTimes(renders)
  const components = { p: ({ children }) => <p>{children}</p> }
  view.rerender(<MarkdownRenderer content="Changed" className="second" components={components} />)
  expect(screen.getByText('Changed').parentElement.className).toContain('second')
  expect(ReactMarkdown.mock.lastCall[0].components.p).toBe(components.p)
  expect(ReactMarkdown).toHaveBeenCalledTimes(renders + 1)
})
