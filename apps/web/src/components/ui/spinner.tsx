import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Spinner: a warm hairline ring with one darker arc.
 *
 * A ring is already a full circle, so the radius tiers do not apply. It reads
 * quiet on purpose: the track is the border hairline and only the leading arc
 * takes the foreground ink.
 */

const sizeClasses = {
  sm: "size-4 border-2",
  md: "size-5 border-2",
  lg: "size-6 border-2",
  xl: "size-8 border-4",
} as const

/** Props for the ring spinner, including its four sizes. */
export interface SpinnerProps extends React.ComponentProps<"div"> {
  /** Ring diameter and stroke weight. Defaults to `md`. */
  size?: keyof typeof sizeClasses
}

/** A quiet loading ring: warm hairline track, one foreground arc. */
function Spinner({ size = "md", className, ...props }: SpinnerProps) {
  return (
    <div
      data-slot="spinner"
      role="status"
      className={cn(
        "animate-spin rounded-full border-border border-t-foreground",
        sizeClasses[size],
        className
      )}
      {...props}
    >
      <span className="sr-only">Loading</span>
    </div>
  )
}

export { Spinner }
