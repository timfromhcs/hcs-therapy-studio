import * as React from "react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldMultiLine } from "./_shared"

/*
 * Loam Textarea: the multi-line field steps back from the pill to the card
 * squircle, because a tall pill reads as a mistake rather than a shape.
 */

/** Multi-line text field on the Loam card squircle. */
const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => (
  <textarea
    data-slot="textarea"
    ref={ref}
    className={cn(formFieldBase, formFieldMultiLine, className)}
    {...props}
  />
))
Textarea.displayName = "Textarea"

export { Textarea }
