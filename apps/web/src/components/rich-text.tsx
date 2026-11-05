/**
 * A deliberately tiny renderer for model output.
 *
 * Model text is untrusted. The usual answer is markdown-to-HTML plus a
 * sanitiser, which is a large dependency and a large attack surface for the four
 * constructs a wellbeing answer actually uses. This renders React elements
 * directly: there is no HTML, no `dangerouslySetInnerHTML`, no link syntax, and
 * therefore no way for a response to inject markup, a script, or a remote image.
 *
 * Supported: paragraphs, `#`-headings, `-`/`•` lists, **bold**, *italic* and
 * `code`. Anything else is passed through as literal text, which is the safe
 * failure mode.
 */

import type { ReactNode } from "react"

function inline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const pattern = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)/g
  let last = 0
  let match: RegExpExecArray | null
  let index = 0
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index))
    const token = match[0]
    const key = `${keyPrefix}-i${index++}`
    if (token.startsWith("**")) {
      nodes.push(
        <strong key={key} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      )
    } else if (token.startsWith("`")) {
      nodes.push(
        <code key={key} className="rounded bg-foreground/10 px-1 py-0.5 font-mono text-[0.9em]">
          {token.slice(1, -1)}
        </code>,
      )
    } else {
      nodes.push(
        <em key={key} className="italic">
          {token.slice(1, -1)}
        </em>,
      )
    }
    last = match.index + token.length
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

export function RichText({ text }: { text: string }) {
  const blocks = text.replace(/\r\n/g, "\n").split(/\n\s*\n/)
  return (
    <div className="flex flex-col gap-2">
      {blocks.map((block, blockIndex) => {
        const trimmed = block.trim()
        if (!trimmed) return null
        const key = `b${blockIndex}`
        if (/^#{1,4}\s/.test(trimmed)) {
          return (
            <p key={key} className="text-sm font-semibold">
              {inline(trimmed.replace(/^#{1,4}\s/, ""), key)}
            </p>
          )
        }
        const lines = trimmed.split("\n")
        if (lines.every((line) => /^\s*[-•*]\s+/.test(line))) {
          return (
            <ul key={key} className="ml-4 list-disc space-y-1">
              {lines.map((line, lineIndex) => (
                <li key={`${key}-l${lineIndex}`}>
                  {inline(line.replace(/^\s*[-•*]\s+/, ""), `${key}-l${lineIndex}`)}
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={key} className="whitespace-pre-wrap break-words">
            {inline(trimmed, key)}
          </p>
        )
      })}
    </div>
  )
}
