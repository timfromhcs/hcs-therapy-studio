import * as React from "react"
import { Toggle as TogglePrimitive } from "@base-ui/react/toggle"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Toggle: a control-tier pill that stays down.
 *
 * Pressed, it takes the primary button's flat near-black fill and the same
 * shadow-xs float, so a held toggle and a hero button read as one material.
 * No gradient and no glow mark the on state, only the fill and the weight.
 */

const toggleVariants = cva(
  [
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap",
    "text-sm font-semibold leading-none",
    "rounded-[var(--radius-control)] cursor-pointer select-none",
    "transition-[transform,background-color,border-color,box-shadow,color] duration-fast ease-out",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50",
    "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
    pressSpring,
    "data-[pressed]:bg-primary data-[pressed]:text-primary-foreground data-[pressed]:[box-shadow:var(--shadow-xs)]",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  ].join(" "),
  {
    variants: {
      variant: {
        // Quiet by default: nothing but text until the pointer or the on state.
        default:
          "bg-transparent text-muted-foreground " +
          "hover:bg-accent hover:text-accent-foreground " +
          "data-[pressed]:hover:bg-primary/90",
        outline:
          "border border-border bg-card text-foreground [box-shadow:var(--shadow-2xs)] " +
          "hover:bg-accent hover:border-foreground/20 hover:text-accent-foreground " +
          "data-[pressed]:border-primary data-[pressed]:hover:bg-primary/90",
      },
      size: {
        sm: "h-8 min-w-8 px-3 text-xs",
        default: "h-10 min-w-10 px-4",
        lg: "h-12 min-w-12 px-5 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

/**
 * A two-state pill. On, it wears the primary button's flat fill.
 *
 * Base UI marks the on state with `data-pressed` where Radix writes
 * `data-state="on"`, so the variants above target that attribute.
 */
function Toggle({
  className,
  variant,
  size,
  ...props
}: React.ComponentProps<typeof TogglePrimitive> &
  VariantProps<typeof toggleVariants>) {
  return (
    <TogglePrimitive
      data-slot="toggle"
      className={cn(toggleVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Toggle, toggleVariants }
