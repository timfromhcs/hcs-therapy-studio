"use client"

import * as React from "react"
import { Search, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine, pressSpring } from "./_shared"

/*
 * Loam SearchInput: the field pill with a lens and a clear button.
 * It is a single-line field, so it wears the shared field recipe on the control
 * tier. Both icons live in the pill's padding, so the field keeps one outline.
 */

/** Search field. The clear button appears once there is something to clear. */
const SearchInput = React.forwardRef<
  HTMLInputElement,
  React.ComponentProps<"input"> & {
    /** Runs when the clear button empties the field. */
    onClear?: () => void
  }
>(({ className, onClear, onChange, value, defaultValue, disabled, ...props }, ref) => {
  const [internal, setInternal] = React.useState(String(defaultValue ?? ""))
  const text = value === undefined ? internal : String(value)
  // The wrapper holds the only ref this component owns, so the caller's `ref`
  // reaches the input untouched.
  const root = React.useRef<HTMLDivElement | null>(null)

  const clear = () => {
    if (value === undefined) {
      setInternal("")
    }
    root.current?.querySelector("input")?.focus()
    onClear?.()
  }

  return (
    <div ref={root} data-slot="search-input" className="relative w-full">
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <input
        ref={ref}
        type="search"
        data-slot="search-input-field"
        value={text}
        disabled={disabled}
        onChange={event => {
          if (value === undefined) {
            setInternal(event.target.value)
          }
          onChange?.(event)
        }}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "pl-11 pr-11",
          "[&::-webkit-search-cancel-button]:appearance-none",
          className
        )}
        {...props}
      />
      {text.length > 0 && (
        <button
          type="button"
          data-slot="search-input-clear"
          onClick={clear}
          disabled={disabled}
          aria-label="Clear search"
          className={cn(
            "absolute right-1.5 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center",
            "cursor-pointer rounded-[var(--radius-control)] text-muted-foreground",
            "transition-[transform,background-color,color] duration-fast ease-out",
            pressSpring,
            "hover:bg-accent hover:text-accent-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:pointer-events-none disabled:opacity-50"
          )}
        >
          <X className="size-4" />
        </button>
      )}
    </div>
  )
})
SearchInput.displayName = "SearchInput"

export { SearchInput }
