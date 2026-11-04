import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam SectionHeader: card tier, because it introduces a whole section.
 *
 * The title comes first, with no label above it. Hierarchy is size and weight,
 * so the title is a clear step above the line under it, and the action pill
 * sits on the right without competing.
 */

/** Props for the section introduction block. */
export interface SectionHeaderProps extends Omit<React.ComponentProps<"div">, "title"> {
  /** The heading text. Always the first thing in the block. */
  title: React.ReactNode
  /** One supporting line under the title. */
  description?: React.ReactNode
  /** Trailing slot, usually a Loam Button. */
  action?: React.ReactNode
  /** Heading level, so the page keeps a sane outline. Defaults to h2. */
  as?: "h1" | "h2" | "h3"
  /** Drop the card surface and keep the type only. */
  plain?: boolean
}

const titleSizes = {
  h1: "text-3xl",
  h2: "text-2xl",
  h3: "text-lg",
} as const

/** A section title with an optional supporting line and a trailing action. */
function SectionHeader({
  className,
  title,
  description,
  action,
  as = "h2",
  plain = false,
  ...props
}: SectionHeaderProps) {
  const Heading = as

  return (
    <div
      data-slot="section-header"
      className={cn(
        "flex flex-wrap items-start justify-between gap-4",
        !plain &&
          "rounded-[var(--radius-card)] border border-border bg-card p-6 text-card-foreground [box-shadow:var(--shadow-sm)]",
        className
      )}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-1.5">
        <Heading
          className={cn(
            titleSizes[as],
            "font-semibold tracking-tight text-balance"
          )}
        >
          {title}
        </Heading>
        {description ? (
          <p className="max-w-prose text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

export { SectionHeader }
