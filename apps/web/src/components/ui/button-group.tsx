import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam ButtonGroup: pills that sit together without merging.
 *
 * Other systems weld a group into one segmented bar with squared inner
 * corners. Loam does not, because a control is always a full pill. The group
 * only sets the direction and the gap, so each button keeps its own shape and
 * the group adds no rim or shadow of its own.
 */

const buttonGroupVariants = cva("flex w-fit items-center", {
  variants: {
    orientation: {
      horizontal: "flex-row gap-2",
      vertical: "flex-col items-stretch gap-2",
    },
  },
  defaultVariants: {
    orientation: "horizontal",
  },
})

/** Props for the group, including its direction. */
export interface ButtonGroupProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof buttonGroupVariants> {
  /** Render the styling onto the single child element instead of a `<div>`. */
  asChild?: boolean
}

/** Lays out related action pills in a row or a column with one shared gap. */
function ButtonGroup({
  className,
  orientation,
  asChild = false,
  ...props
}: ButtonGroupProps) {
  const Comp = asChild ? Slot : "div"

  return (
    <Comp
      data-slot="button-group"
      data-orientation={orientation ?? "horizontal"}
      role="group"
      className={cn(buttonGroupVariants({ orientation }), className)}
      {...props}
    />
  )
}

/** A warm hairline that splits a group into two sets of actions. */
function ButtonGroupSeparator({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<"div"> & {
  /** Which way the rule runs. Vertical suits a horizontal group. */
  orientation?: "horizontal" | "vertical"
}) {
  return (
    <div
      data-slot="button-group-separator"
      data-orientation={orientation}
      role="separator"
      aria-orientation={orientation}
      className={cn(
        "shrink-0 self-stretch bg-border",
        orientation === "vertical" ? "my-1 w-px" : "mx-1 h-px",
        className
      )}
      {...props}
    />
  )
}

/** A static label or prefix inside a group, shaped like the pills beside it. */
function ButtonGroupText({
  className,
  asChild = false,
  ...props
}: React.ComponentProps<"div"> & {
  /** Render the styling onto the single child element instead of a `<div>`. */
  asChild?: boolean
}) {
  const Comp = asChild ? Slot : "div"

  return (
    <Comp
      data-slot="button-group-text"
      className={cn(
        "inline-flex h-10 shrink-0 items-center gap-2 whitespace-nowrap",
        "rounded-[var(--radius-control)] border border-border bg-secondary px-4",
        "text-sm font-semibold text-secondary-foreground",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

export { ButtonGroup, ButtonGroupSeparator, ButtonGroupText, buttonGroupVariants }
