import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam AspectRatio: a media box that holds its shape.
 *
 * The ratio box sits at the card tier, because it frames media rather than
 * acting as a control. It clips its child so a photo picks up the same
 * squircle every Loam card uses.
 */

/**
 * Holds a child at a fixed width to height ratio, clipped to the card squircle.
 *
 * Base UI ships no aspect-ratio primitive, so this keeps the Radix-shaped
 * `ratio` prop and sets the CSS `aspect-ratio` property directly.
 */
function AspectRatio({
  className,
  ratio = 1,
  style,
  ...props
}: React.ComponentProps<"div"> & {
  /** Width divided by height, so `16 / 9` is a widescreen frame. */
  ratio?: number
}) {
  return (
    <div
      data-slot="aspect-ratio"
      style={{ aspectRatio: ratio, ...style }}
      className={cn(
        "w-full overflow-hidden rounded-[var(--radius-card)] bg-muted",
        className
      )}
      {...props}
    />
  )
}

export { AspectRatio }
