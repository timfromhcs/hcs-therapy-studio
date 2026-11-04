import * as React from "react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine } from "./_shared"

/*
 * Loam Input: a near-white pill field in the cream page.
 * The control tier of the radius scale, held by a warm hairline, focused with
 * the blue ring.
 */

/** Single-line text field on the Loam pill shape. */
const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      data-slot="input"
      ref={ref}
      className={cn(
        formFieldBase,
        formFieldSingleLine,
        "file:border-0 file:bg-transparent file:text-sm file:font-semibold",
        className
      )}
      {...props}
    />
  )
)
Input.displayName = "Input"

export { Input }
