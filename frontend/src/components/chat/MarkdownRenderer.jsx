import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { cn } from '@/lib/utils'
import { CodeBlock } from './CodeBlock'

const components = {
  code: ({ node, children, ...props }) => {
    const isInline = !node.children?.some(c => c.type === 'text' && c.value.includes('\n'))
    if (isInline) {
      return <code className="bg-accent px-1.5 py-0.5 rounded text-sm font-mono" {...props}>{children}</code>
    }
    return <CodeBlock {...props} codeString={children} language={node.data?.meta || ''} />
  },
  pre: ({ children, ...props }) => {
    return <div className="relative my-4 rounded-lg border border-border bg-muted p-4 overflow-x-auto" {...props}>{children}</div>
  },
  p: ({ children, ...props }) => <p className="my-3 leading-7" {...props}>{children}</p>,
  h1: ({ children, ...props }) => <h1 className="text-2xl font-bold mt-6 mb-3" {...props}>{children}</h1>,
  h2: ({ children, ...props }) => <h2 className="text-xl font-semibold mt-5 mb-2" {...props}>{children}</h2>,
  h3: ({ children, ...props }) => <h3 className="text-lg font-medium mt-4 mb-2" {...props}>{children}</h3>,
  ul: ({ children, ...props }) => <ul className="list-disc list-inside my-3 space-y-1" {...props}>{children}</ul>,
  ol: ({ children, ...props }) => <ol className="list-decimal list-inside my-3 space-y-1" {...props}>{children}</ol>,
  li: ({ children, ...props }) => <li className="ml-4" {...props}>{children}</li>,
  blockquote: ({ children, ...props }) => (
    <blockquote className="border-l-4 border-primary pl-4 italic my-3 text-muted-foreground" {...props}>
      {children}
    </blockquote>
  ),
  a: ({ href, children, ...props }) => (
    <a 
      href={href} 
      target="_blank" 
      rel="noopener noreferrer" 
      className="text-primary underline underline-offset-2 hover:no-underline" 
      {...props}
    >
      {children}
    </a>
  ),
  table: ({ children, ...props }) => (
    <div className="overflow-x-auto my-4">
      <table className="w-full border-collapse border border-border" {...props}>
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-muted/50" {...props}>{children}</thead>
  ),
  tbody: ({ children, ...props }) => <tbody {...props}>{children}</tbody>,
  tr: ({ children, ...props }) => <tr className="border-t border-border" {...props}>{children}</tr>,
  th: ({ children, ...props }) => (
    <th className="px-3 py-2 text-left font-semibold border border-border" {...props}>{children}</th>
  ),
  td: ({ children, ...props }) => (
    <td className="px-3 py-2 border border-border" {...props}>{children}</td>
  ),
  hr: () => <hr className="my-6 border-border" />,
  strong: ({ children, ...props }) => <strong className="font-semibold" {...props}>{children}</strong>,
  em: ({ children, ...props }) => <em className="italic" {...props}>{children}</em>,
  del: ({ children, ...props }) => <del className="line-through" {...props}>{children}</del>,
}

export function MarkdownRenderer({ 
  content, 
  className,
  components: customComponents 
}) {
  return (
    <div className={cn('prose prose-sm dark:prose-invert max-w-none', className)}>
      <ReactMarkdown
        components={{ ...components, ...customComponents }}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export function InlineMarkdown({ content }) {
  return (
    <ReactMarkdown
      components={{
        code: ({ children, ...props }) => (
          <code className="bg-accent px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
            {children}
          </code>
        ),
        a: ({ href, children, ...props }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline" {...props}>
            {children}
          </a>
        ),
      }}
      remarkPlugins={[remarkGfm]}
    >
      {content}
    </ReactMarkdown>
  )
}