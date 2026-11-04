"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { CopyButton } from "./copy-button"

/*
 * Loam CodeBlock: a card-tier muted surface.
 *
 * Code is a card, so it takes the card radius (1.5rem) and clips its content
 * with overflow-hidden, which keeps long lines inside the squircle. The
 * surface is the warm muted neutral, never a cold slab.
 */

/** Props for the code surface. */
export interface CodeBlockProps extends React.ComponentProps<"div"> {
  /** The source text to display. */
  code: string
  /** Language name, used for the label and the `language-` class. */
  lang?: string
  /** Filename or path shown in the header strip. */
  filename?: string
  /** Show the copy pill in the header strip. Defaults to true. */
  copyable?: boolean
}

/** The header strip above the code: a filename on the left, actions right. */
function CodeBlockHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="code-block-header"
      className={cn(
        "flex items-center justify-between gap-3 border-b border-border px-4 py-2",
        "font-mono text-xs text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/** The scrolling code area itself. */
function CodeBlockCode({
  className,
  ...props
}: React.ComponentProps<"pre">) {
  return (
    <pre
      data-slot="code-block-code"
      className={cn(
        "m-0 overflow-x-auto bg-transparent p-4 font-mono text-xs leading-relaxed text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** A card-tier code surface on the warm muted neutral, with a copy pill. */
function CodeBlock({
  code,
  lang,
  filename,
  copyable = true,
  className,
  ...props
}: CodeBlockProps) {
  const showHeader = Boolean(filename) || copyable

  return (
    <div
      data-slot="code-block"
      className={cn(
        "w-full overflow-hidden rounded-[var(--radius-card)] border border-border",
        "bg-muted font-mono",
        className
      )}
      {...props}
    >
      {showHeader ? (
        <CodeBlockHeader>
          <span className="truncate">{filename ?? lang ?? "code"}</span>
          {copyable ? <CopyButton value={code} /> : null}
        </CodeBlockHeader>
      ) : null}

      <CodeBlockCode>
        <code className={lang ? `language-${lang}` : undefined}>{code}</code>
      </CodeBlockCode>
    </div>
  )
}

export { CodeBlock, CodeBlockHeader, CodeBlockCode }
