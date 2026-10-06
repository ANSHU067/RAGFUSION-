import React from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'

const languageLabels = {
  js: 'JavaScript',
  ts: 'TypeScript',
  jsx: 'JSX',
  tsx: 'TSX',
  py: 'Python',
  rb: 'Ruby',
  go: 'Go',
  rs: 'Rust',
  java: 'Java',
  cpp: 'C++',
  c: 'C',
  cs: 'C#',
  php: 'PHP',
  html: 'HTML',
  css: 'CSS',
  scss: 'SCSS',
  json: 'JSON',
  yaml: 'YAML',
  xml: 'XML',
  sql: 'SQL',
  sh: 'Shell',
  bash: 'Bash',
  zsh: 'Zsh',
  md: 'Markdown',
  txt: 'Text',
}

function normalizeCodeString(value) {
  if (typeof value === 'string') return value
  if (value == null || typeof value === 'boolean') return ''
  if (typeof value === 'number' || typeof value === 'bigint') return String(value)

  if (Array.isArray(value)) {
    return value.map(normalizeCodeString).join('')
  }

  // rehype-highlight can wrap code in React elements. Extract their text
  // children instead of rendering an object or attempting string methods on it.
  if (React.isValidElement(value)) {
    return normalizeCodeString(value.props.children)
  }

  return String(value)
}

export function CodeBlock({ 
  codeString, 
  language = '', 
  showLineNumbers = false,
  maxHeight = 400,
  className 
}) {
  const [copied, setCopied] = React.useState(false)
  const [expanded, setExpanded] = React.useState(false)
  const normalizedCode = React.useMemo(() => normalizeCodeString(codeString), [codeString])
  const lines = React.useMemo(() => normalizedCode.split('\n'), [normalizedCode])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(normalizedCode)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { setCopied(false) }
  }

  const langLabel = languageLabels[language.toLowerCase()] || language.toUpperCase() || 'CODE'

  return (
    <div className={cn('relative group', className)}>
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border rounded-t-lg">
        <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
          {langLabel}
        </span>
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleCopy}
            aria-label={copied ? 'Copied!' : 'Copy code'}
          >
            {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
          </Button>
          {lines.length > 20 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setExpanded(!expanded)}
              aria-label={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          )}
        </div>
      </div>

      <pre className={cn(
        'overflow-x-auto p-3 font-mono text-sm leading-relaxed',
        'bg-muted/50 rounded-b-lg',
        expanded ? 'max-h-none' : `max-h-[${maxHeight}px]`
      )}>
        {showLineNumbers && (
          <span className="select-none mr-4 text-muted-foreground/50 w-8 text-right inline-block pr-2 border-r border-border">
            {lines.map((_, i) => <div key={i}>{i + 1}</div>)}
          </span>
        )}
        <code className="text-foreground">
          {expanded || lines.length <= 20 
            ? normalizedCode
            : lines.slice(0, 20).join('\n') + '\n...'
          }
        </code>
      </pre>

      {lines.length > 20 && !expanded && (
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-muted/50 to-transparent pointer-events-none" />
      )}
    </div>
  )
}

export function InlineCode({ children, className }) {
  return (
    <code className={cn('bg-accent px-1.5 py-0.5 rounded text-sm font-mono', className)}>
      {children}
    </code>
  )
}
