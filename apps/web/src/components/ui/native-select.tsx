import * as React from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine } from "./_shared"

/*
 * Loam NativeSelect: the browser's own select on the Loam field pill.
 * It is a single-line field, so it takes the control tier and the shared field
 * recipe. The chevron sits in the padding, because the native arrow cannot be
 * styled to match the warm hairline.
 */

/** The platform select, wearing the Loam field pill. */
const NativeSelect = React.forwardRef<
  HTMLSelectElement,
  React.ComponentProps<"select">
>(({ className, children, ...props }, ref) => (
  <span data-slot="native-select-wrapper" className="relative block w-full">
    <select
      ref={ref}
      data-slot="native-select"
      className={cn(
        formFieldBase,
        formFieldSingleLine,
        "cursor-pointer appearance-none bg-none pr-11",
        className
      )}
      {...props}
    >
      {children}
    </select>
    <ChevronDown
      aria-hidden="true"
      className="pointer-events-none absolute right-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
    />
  </span>
))
NativeSelect.displayName = "NativeSelect"

/** One option inside a NativeSelect. It inherits the page ink and surface. */
const NativeSelectOption = React.forwardRef<
  HTMLOptionElement,
  React.ComponentProps<"option">
>(({ className, ...props }, ref) => (
  <option
    ref={ref}
    data-slot="native-select-option"
    className={cn("bg-popover text-popover-foreground", className)}
    {...props}
  />
))
NativeSelectOption.displayName = "NativeSelectOption"

export { NativeSelect, NativeSelectOption }
