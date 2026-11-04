"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam ThinkingIndicator: the quietest live state in the system.
 *
 * Three muted dots on a control pill, so it can sit inline in a message row.
 * No colour and no shadow: an agent that is still working should not compete
 * with the answer it is about to give.
 */

/** Props for the inline thinking tell. */
export interface ThinkingIndicatorProps extends React.ComponentProps<"div"> {
  /** The line shown beside the dots. Defaults to `Thinking`. */
  label?: string
  /** Hide the label and show only the three dots. */
  compact?: boolean
}

/** A soft three-dot tell that the agent is still working. */
function ThinkingIndicator({
  label = "Thinking",
  compact = false,
  className,
  ...props
}: ThinkingIndicatorProps) {
  return (
    <div
      data-slot="thinking-indicator"
      role="status"
      aria-live="polite"
      className={cn(
        "inline-flex items-center gap-2 rounded-[var(--radius-control)]",
        "bg-muted px-3 py-1.5 text-sm text-muted-foreground",
        className
      )}
      {...props}
    >
      <span aria-hidden="true" className="flex items-center gap-1">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="size-1.5 animate-pulse rounded-full bg-muted-foreground/60"
            style={{ animationDelay: `${dot * 180}ms`, animationDuration: "1.2s" }}
          />
        ))}
      </span>
      {compact ? <span className="sr-only">{label}</span> : <span>{label}</span>}
    </div>
  )
}

export { ThinkingIndicator }
