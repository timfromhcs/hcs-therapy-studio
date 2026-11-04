import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam StatusIndicator: a control pill carrying a dot and a word.
 *
 * Each state draws one pop triad: the soft surface, the hairline in the same
 * hue and ink dark enough to read on it. The dot never travels alone, because
 * colour on its own is not a label.
 */

/** Class recipe for the status pill, one pop triad per state. */
const statusIndicatorVariants = cva(
  "inline-flex w-fit shrink-0 items-center gap-2 " +
    "rounded-[var(--radius-control)] border px-2.5 py-1 " +
    "text-xs font-semibold whitespace-nowrap",
  {
    variants: {
      status: {
        online: "border-pop-green-border bg-pop-green-surface text-pop-green-ink",
        success: "border-pop-green-border bg-pop-green-surface text-pop-green-ink",
        busy: "border-pop-red-border bg-pop-red-surface text-pop-red-ink",
        error: "border-pop-red-border bg-pop-red-surface text-pop-red-ink",
        away: "border-pop-amber-border bg-pop-amber-surface text-pop-amber-ink",
        warning: "border-pop-orange-border bg-pop-orange-surface text-pop-orange-ink",
        info: "border-pop-blue-border bg-pop-blue-surface text-pop-blue-ink",
        pending: "border-pop-purple-border bg-pop-purple-surface text-pop-purple-ink",
        offline: "border-pop-neutral-border bg-pop-neutral-surface text-pop-neutral-ink",
        neutral: "border-pop-neutral-border bg-pop-neutral-surface text-pop-neutral-ink",
      },
      size: {
        sm: "px-2 py-0.5 text-xs",
        default: "px-2.5 py-1 text-xs",
        lg: "px-3 py-1.5 text-sm",
      },
    },
    defaultVariants: {
      status: "neutral",
      size: "default",
    },
  }
)

/** Props for the status pill, including its state and size. */
export interface StatusIndicatorProps
  extends React.ComponentProps<"span">,
    VariantProps<typeof statusIndicatorVariants> {
  /** Word shown beside the dot. Falls back to the status name. */
  label?: string
  /** Animate the dot, for a state that is still moving. */
  pulse?: boolean
}

/** A dot plus a word, in the pop triad for its state. */
function StatusIndicator({
  className,
  status = "neutral",
  size,
  label,
  pulse = false,
  children,
  ...props
}: StatusIndicatorProps) {
  const text = children ?? label ?? status

  return (
    <span
      data-slot="status-indicator"
      data-status={status}
      className={cn(statusIndicatorVariants({ status, size }), className)}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-1.5 shrink-0 rounded-[var(--radius-control)] bg-current",
          pulse && "animate-pulse"
        )}
      />
      {text}
    </span>
  )
}

export { StatusIndicator, statusIndicatorVariants }
