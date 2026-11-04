import * as React from "react"
import { Separator as SeparatorPrimitive } from "@base-ui/react/separator"

import { cn } from "@/lib/utils"

/*
 * Loam Separator: a warm hairline.
 *
 * A separator has no radius tier of its own, because it is a line rather than
 * a surface. It borrows the same border token every card rim uses, so one rule
 * governs every edge in the system.
 */

/**
 * A one pixel warm rule that divides content horizontally or vertically.
 *
 * Base UI has no `decorative` prop and always exposes the separator role, so
 * this keeps the Radix-shaped prop and drops the role when the rule is only
 * visual.
 */
function Separator({
  className,
  orientation = "horizontal",
  decorative = true,
  ...props
}: React.ComponentProps<typeof SeparatorPrimitive> & {
  /** Hide the rule from assistive technology when it carries no meaning. */
  decorative?: boolean
}) {
  return (
    <SeparatorPrimitive
      data-slot="separator"
      orientation={orientation}
      role={decorative ? "none" : "separator"}
      className={cn(
        "shrink-0 bg-border",
        "data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full",
        "data-[orientation=vertical]:h-full data-[orientation=vertical]:w-px",
        className
      )}
      {...props}
    />
  )
}

export { Separator }
