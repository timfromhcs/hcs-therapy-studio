import * as React from "react"
import { Radio as RadioPrimitive } from "@base-ui/react/radio"
import { RadioGroup as RadioGroupPrimitive } from "@base-ui/react/radio-group"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam RadioGroup: a near-white circle that fills with the flat near-black
 * primary when selected, so the dot and the hero pill read as one material.
 */

/** Vertical group wrapper for Loam radio items. */
const RadioGroup = React.forwardRef<
  React.ElementRef<typeof RadioGroupPrimitive>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive>
>(({ className, ...props }, ref) => (
  <RadioGroupPrimitive
    ref={ref}
    data-slot="radio-group"
    className={cn("grid gap-2.5", className)}
    {...props}
  />
))
RadioGroup.displayName = "RadioGroup"

/**
 * One radio option, filling with the primary material when selected.
 *
 * Base UI splits Radix's single `RadioGroup.Item` into a `Radio.Root` from its
 * own module, so this export keeps the Radix name and renders that part.
 */
const RadioGroupItem = React.forwardRef<
  React.ElementRef<typeof RadioPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof RadioPrimitive.Root>
>(({ className, ...props }, ref) => (
  <RadioPrimitive.Root
    ref={ref}
    data-slot="radio-group-item"
    className={cn(
      "aspect-square size-4 shrink-0 rounded-[var(--radius-control)] border border-border bg-input",
      "cursor-pointer transition-[transform,background-color,border-color,box-shadow] duration-fast ease-out",
      pressSpring,
      "hover:border-foreground/20",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50",
      "data-[checked]:border-primary data-[checked]:bg-primary",
      "data-[checked]:[box-shadow:var(--shadow-xs)]",
      className
    )}
    {...props}
  >
    <RadioPrimitive.Indicator
      data-slot="radio-group-indicator"
      className="grid size-full place-items-center data-[unchecked]:hidden"
    >
      <span className="block size-1.5 rounded-[var(--radius-control)] bg-primary-foreground" />
    </RadioPrimitive.Indicator>
  </RadioPrimitive.Root>
))
RadioGroupItem.displayName = "RadioGroupItem"

export { RadioGroup, RadioGroupItem }
