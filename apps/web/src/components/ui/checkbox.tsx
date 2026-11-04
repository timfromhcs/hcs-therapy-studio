import * as React from "react"
import { Checkbox as CheckboxPrimitive } from "@base-ui/react/checkbox"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Checkbox: a near-white field box when empty, the flat near-black fill
 * when checked. It reuses the primary Button's flat fill, so a ticked
 * box and a hero pill are visibly the same material. It also shares the spring
 * press, so the whole system responds alike.
 *
 * The box keeps a small squircle rather than the full pill: a 16px pill would
 * be a circle, which reads as a radio.
 */

/** The Radix-shaped tri-state value: on, off, or mixed. */
export type CheckboxCheckedState = boolean | "indeterminate"

/** Props for the Loam checkbox, keeping Radix's tri-state `checked`. */
export interface CheckboxProps
  extends Omit<
    React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>,
    "checked" | "defaultChecked" | "onCheckedChange" | "className"
  > {
  /** Extra classes for the box. */
  className?: string
  /** `true`, `false`, or `"indeterminate"` for the mixed state. */
  checked?: CheckboxCheckedState
  /** Starting value when the checkbox is uncontrolled. */
  defaultChecked?: CheckboxCheckedState
  /** Fires with the new tri-state value. */
  onCheckedChange?: (checked: CheckboxCheckedState) => void
}

/**
 * A checkbox whose checked fill matches the Loam primary button.
 *
 * Base UI splits Radix's `checked="indeterminate"` into a separate
 * `indeterminate` boolean, so this wrapper keeps the Radix-shaped tri-state
 * prop and maps it onto the two Base UI props.
 */
const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  CheckboxProps
>(
  (
    { className, checked, defaultChecked, onCheckedChange, ...props },
    ref
  ) => {
    const isMixed =
      checked === "indeterminate" || defaultChecked === "indeterminate"

    return (
      <CheckboxPrimitive.Root
        ref={ref}
        data-slot="checkbox"
        indeterminate={isMixed}
        checked={checked === "indeterminate" ? false : checked}
        defaultChecked={
          defaultChecked === "indeterminate" ? false : defaultChecked
        }
        onCheckedChange={(next) => onCheckedChange?.(next)}
        className={cn(
          "peer size-4 shrink-0 rounded-sm border border-border bg-input",
          "cursor-pointer transition-[transform,background-color,border-color,box-shadow] duration-fast ease-out",
          pressSpring,
          "hover:border-foreground/20",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50",
          "data-[checked]:bg-primary data-[checked]:border-primary data-[checked]:text-primary-foreground",
          "data-[checked]:[box-shadow:var(--shadow-xs)]",
          "data-[indeterminate]:bg-primary data-[indeterminate]:border-primary data-[indeterminate]:text-primary-foreground",
          className
        )}
        {...props}
      >
        <CheckboxPrimitive.Indicator
          keepMounted
          data-slot="checkbox-indicator"
          className="grid size-full place-items-center text-current data-[unchecked]:hidden"
        >
          <Check className="size-3" strokeWidth={3} />
        </CheckboxPrimitive.Indicator>
      </CheckboxPrimitive.Root>
    )
  }
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
