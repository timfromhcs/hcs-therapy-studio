import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Label: the field caption.
 * Labels carry no surface of their own, so they take no radius tier. Loam's
 * type rule gives them the semibold weight that buttons use, so a caption and
 * its control read as one pair.
 */

/**
 * Caption for a form control.
 *
 * Base UI has no standalone label primitive. Its only label is `Field.Label`,
 * which needs a `Field.Root` around it, so this renders a plain `<label>` and
 * keeps the Radix-shaped props the rest of the kit passes.
 */
const Label = React.forwardRef<
  HTMLLabelElement,
  React.ComponentPropsWithoutRef<"label">
>(({ className, ...props }, ref) => (
  <label
    ref={ref}
    data-slot="label"
    className={cn(
      "flex select-none items-center gap-2 text-sm font-semibold leading-none text-foreground",
      "group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50",
      "peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
      className
    )}
    {...props}
  />
))
Label.displayName = "Label"

export { Label }
