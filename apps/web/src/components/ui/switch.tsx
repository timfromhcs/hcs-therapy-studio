"use client"

import * as React from "react"
import { Switch as SwitchPrimitive } from "@base-ui/react/switch"

import { cn } from "@/lib/utils"

/*
 * Loam Switch: a near-white track that becomes the flat near-black fill when
 * on, the same material as the primary Button. The thumb is a small white knob
 * with the softest float in the scale.
 *
 * The track is already a pill, so it needs no radius decision: it is the
 * control tier by nature.
 */

/**
 * A switch whose on-state track matches the Loam primary button fill.
 *
 * Base UI marks the on state with `data-checked` where Radix writes
 * `data-state="checked"`, so the variants below target the Base UI attribute.
 */
const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitive.Root
    ref={ref}
    data-slot="switch"
    className={cn(
      "peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center",
      "rounded-[var(--radius-control)] border border-border bg-input",
      "transition-[background-color,border-color,box-shadow] duration-fast ease-out",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50",
      "data-[checked]:border-primary data-[checked]:bg-primary",
      "data-[checked]:[box-shadow:var(--shadow-xs)]",
      className
    )}
    {...props}
  >
    <SwitchPrimitive.Thumb
      data-slot="switch-thumb"
      className={cn(
        "pointer-events-none block size-4 rounded-[var(--radius-control)] bg-card",
        "[box-shadow:var(--shadow-2xs)]",
        "transition-transform duration-fast ease-out",
        "data-[unchecked]:translate-x-0.5 data-[checked]:translate-x-[1.125rem]"
      )}
    />
  </SwitchPrimitive.Root>
))
Switch.displayName = "Switch"

export { Switch }
