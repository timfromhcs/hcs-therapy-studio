import * as React from "react"
import { Minus, Plus } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine, pressSpring } from "./_shared"

/*
 * Loam NumberInput: the field pill with a step pair.
 * It is a single-line field, so it wears the shared field recipe on the control
 * tier. The two steppers are ghost pills inside the field's right padding, so
 * the row reads as one control rather than three.
 */

/** Numeric field with minus and plus steppers. */
const NumberInput = React.forwardRef<
  HTMLInputElement,
  Omit<React.ComponentProps<"input">, "type"> & {
    /** How much one press of a stepper moves the value. Defaults to 1. */
    step?: number
  }
>(({ className, step = 1, min, max, disabled, ...props }, ref) => {
  const root = React.useRef<HTMLDivElement | null>(null)

  const nudge = (direction: 1 | -1) => {
    const field = root.current?.querySelector("input")
    if (!field) {
      return
    }
    if (direction === 1) {
      field.stepUp()
    } else {
      field.stepDown()
    }
    field.dispatchEvent(new Event("input", { bubbles: true }))
    field.focus()
  }

  const stepperClass = cn(
    "flex size-7 items-center justify-center",
    "cursor-pointer rounded-[var(--radius-control)] text-muted-foreground",
    "transition-[transform,background-color,color] duration-fast ease-out",
    pressSpring,
    "hover:bg-accent hover:text-accent-foreground",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50"
  )

  return (
    <div ref={root} data-slot="number-input" className="relative w-full">
      <input
        ref={ref}
        type="number"
        inputMode="decimal"
        data-slot="number-input-field"
        step={step}
        min={min}
        max={max}
        disabled={disabled}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "pr-20 tabular-nums",
          "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none",
          className
        )}
        {...props}
      />
      <div className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
        <button
          type="button"
          data-slot="number-input-decrement"
          onClick={() => nudge(-1)}
          disabled={disabled}
          aria-label="Decrease"
          className={stepperClass}
        >
          <Minus className="size-4" />
        </button>
        <button
          type="button"
          data-slot="number-input-increment"
          onClick={() => nudge(1)}
          disabled={disabled}
          aria-label="Increase"
          className={stepperClass}
        >
          <Plus className="size-4" />
        </button>
      </div>
    </div>
  )
})
NumberInput.displayName = "NumberInput"

export { NumberInput }
