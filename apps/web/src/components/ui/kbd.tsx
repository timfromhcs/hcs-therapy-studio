import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Kbd: a very small mono pill, so it takes the control radius.
 *
 * It sits on the muted paper tone behind a warm hairline, one step quieter than
 * the surrounding text, because a shortcut supports the sentence rather than
 * leading it.
 */

/** A single key cap for a keyboard shortcut. */
function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      data-slot="kbd"
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center",
        "rounded-[var(--radius-control)] border border-border bg-muted px-1.5",
        "font-mono text-xs font-semibold text-muted-foreground select-none",
        className
      )}
      {...props}
    />
  )
}

/** A run of key caps, for a chord such as Command then K. */
function KbdGroup({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="kbd-group"
      className={cn("inline-flex items-center gap-1", className)}
      {...props}
    />
  )
}

export { Kbd, KbdGroup }
