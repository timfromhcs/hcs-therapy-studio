"use client"

import * as React from "react"
import { Check, Copy } from "lucide-react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam CopyButton: an icon control, so it takes the control tier (full pill).
 *
 * It shares the system press spring, and the glyph swaps to a tick for a
 * moment after a successful copy. The tick takes the green pop ink, which is
 * the only colour allowed on a chrome control.
 */

/** Props for the copy control. */
export interface CopyButtonProps
  extends Omit<React.ComponentProps<"button">, "children"> {
  /** The text to write to the clipboard. */
  value: string
  /** Optional label rendered beside the glyph. */
  label?: string
  /** How long the tick stays visible, in milliseconds. Defaults to 1600. */
  resetAfter?: number
  /** Runs after the text reaches the clipboard. */
  onCopied?: (value: string) => void
}

/** An icon pill that copies text and swaps its glyph to a tick on success. */
function CopyButton({
  value,
  label,
  resetAfter = 1600,
  onCopied,
  className,
  onClick,
  ...props
}: CopyButtonProps) {
  const [copied, setCopied] = React.useState(false)
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    []
  )

  const handleClick = async (event: React.MouseEvent<HTMLButtonElement>) => {
    onClick?.(event)
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      return
    }

    onCopied?.(value)
    setCopied(true)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setCopied(false), resetAfter)
  }

  return (
    <button
      type="button"
      data-slot="copy-button"
      data-copied={copied ? "true" : "false"}
      aria-label={label ?? (copied ? "Copied" : "Copy")}
      onClick={handleClick}
      className={cn(
        "inline-flex shrink-0 cursor-pointer select-none items-center justify-center gap-2",
        "rounded-[var(--radius-control)] border border-border bg-card",
        "text-xs font-semibold text-muted-foreground",
        label ? "h-8 px-3.5" : "size-8",
        "[box-shadow:var(--shadow-2xs)]",
        "transition-[transform,background-color,border-color,color] duration-fast ease-out",
        "hover:bg-accent hover:border-foreground/20 hover:text-accent-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        pressSpring,
        className
      )}
      {...props}
    >
      {copied ? (
        <Check className="size-3.5 text-pop-green-ink" />
      ) : (
        <Copy className="size-3.5" />
      )}
      {label ? <span>{copied ? "Copied" : label}</span> : null}
    </button>
  )
}

export { CopyButton }
