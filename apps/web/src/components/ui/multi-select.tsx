"use client"

import * as React from "react"
import * as PopoverPrimitive from "@radix-ui/react-popover"
import { Check, ChevronDown, X } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  floatingSurfaceBase,
  formFieldBase,
  formFieldSingleLine,
  menuItemBase,
  pressSpring,
} from "./_shared"

/*
 * Loam MultiSelect: a field pill that holds chips and opens a card.
 * The closed control is a single-line field, so it wears the shared field
 * recipe on the control tier and grows downward as chips wrap. The list floats
 * on the card squircle, and each row is a menu pill.
 */

/** One choice in a MultiSelect. */
export interface MultiSelectOption {
  /** The stored value. */
  value: string
  /** The text shown in the list and in the chip. */
  label: string
  disabled?: boolean
}

/** Props for the Loam multi select. */
export interface MultiSelectProps {
  /** The choices to offer. */
  options: MultiSelectOption[]
  /** Chosen values when you drive the control yourself. */
  value?: string[]
  /** Chosen values the control starts with when it drives itself. */
  defaultValue?: string[]
  /** Runs after every add or remove, with the full new selection. */
  onValueChange?: (value: string[]) => void
  placeholder?: string
  /** Shows a count chip once the selection passes this many items. */
  maxDisplay?: number
  disabled?: boolean
  className?: string
}

/** A select that keeps several values, each shown as a removable chip. */
function MultiSelect({
  options,
  value,
  defaultValue,
  onValueChange,
  placeholder = "Select options",
  maxDisplay = 3,
  disabled,
  className,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [internal, setInternal] = React.useState<string[]>(defaultValue ?? [])
  const selected = value ?? internal

  const commit = (next: string[]) => {
    if (value === undefined) {
      setInternal(next)
    }
    onValueChange?.(next)
  }

  const toggle = (optionValue: string) => {
    commit(
      selected.includes(optionValue)
        ? selected.filter(item => item !== optionValue)
        : [...selected, optionValue]
    )
  }

  const chips = options.filter(option => selected.includes(option.value))
  const shown = chips.slice(0, maxDisplay)
  const overflow = chips.length - shown.length

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger
        data-slot="multi-select-trigger"
        disabled={disabled}
        aria-label={placeholder}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "h-auto min-h-10 cursor-pointer flex-wrap justify-between gap-1.5 py-1.5 text-left",
          className
        )}
      >
        <span className="flex min-w-0 flex-wrap items-center gap-1.5">
          {chips.length === 0 ? (
            <span className="text-muted-foreground">{placeholder}</span>
          ) : (
            shown.map(option => (
              <span
                key={option.value}
                data-slot="multi-select-chip"
                className="inline-flex items-center gap-1 rounded-[var(--radius-control)] border border-border bg-secondary px-2.5 py-0.5 text-xs font-semibold text-secondary-foreground"
              >
                {option.label}
                <X
                  aria-hidden="true"
                  className="size-3 text-muted-foreground transition-colors duration-fast hover:text-foreground"
                  onClick={event => {
                    event.preventDefault()
                    event.stopPropagation()
                    toggle(option.value)
                  }}
                />
              </span>
            ))
          )}
          {overflow > 0 && (
            <span className="text-xs font-semibold text-muted-foreground">
              and {overflow} more
            </span>
          )}
        </span>
        <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
      </PopoverPrimitive.Trigger>

      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          data-slot="multi-select-content"
          align="start"
          sideOffset={6}
          className={cn(
            floatingSurfaceBase,
            "z-50 max-h-72 w-[var(--radix-popover-trigger-width)] overflow-y-auto p-1.5",
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          )}
        >
          <div role="listbox" aria-multiselectable="true" className="flex flex-col">
            {options.map(option => {
              const isSelected = selected.includes(option.value)
              return (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  disabled={option.disabled}
                  data-slot="multi-select-item"
                  data-disabled={option.disabled ? "" : undefined}
                  onClick={() => toggle(option.value)}
                  className={cn(
                    menuItemBase,
                    pressSpring,
                    "w-full cursor-pointer justify-between text-left hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <span className="truncate">{option.label}</span>
                  {isSelected && <Check className="size-4" strokeWidth={3} />}
                </button>
              )
            })}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}

export { MultiSelect }
