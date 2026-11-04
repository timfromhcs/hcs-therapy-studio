import * as React from "react"
import { Progress as ProgressPrimitive } from "@base-ui/react/progress"

import { cn } from "@/lib/utils"

/*
 * Loam Progress: a control-tier pill that fills with the primary material.
 *
 * The track is the same near-white field surface as an input, held by the warm
 * hairline, and the filled part is the flat near-black of the primary Button.
 * A bar this short is a pill by nature, so it takes the control radius.
 */

/**
 * A determinate progress pill whose fill matches the Loam primary button.
 *
 * Base UI splits the bar into Root, Track and Indicator, where Radix has Root
 * and Indicator, so this adds the Track part and keeps the Radix-shaped props.
 */
function Progress({
  className,
  value = 0,
  ...props
}: Omit<React.ComponentProps<typeof ProgressPrimitive.Root>, "value"> & {
  /** How far along, from `min` to `max`. `null` shows the indeterminate bar. */
  value?: number | null
}) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      value={value}
      className={cn("w-full", className)}
      {...props}
    >
      <ProgressPrimitive.Track
        data-slot="progress-track"
        className="relative h-2 w-full overflow-hidden rounded-[var(--radius-control)] border border-border bg-input"
      >
        <ProgressPrimitive.Indicator
          data-slot="progress-indicator"
          className="h-full bg-primary transition-[width] duration-slow ease-out"
        />
      </ProgressPrimitive.Track>
    </ProgressPrimitive.Root>
  )
}

export { Progress }
