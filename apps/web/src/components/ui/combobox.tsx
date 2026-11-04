import * as React from "react"
import * as PopoverPrimitive from "@radix-ui/react-popover"
import { Check, ChevronsUpDown, Search } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  floatingSurfaceBase,
  formFieldBase,
  formFieldSingleLine,
  menuItemBase,
  pressSpring,
} from "./_shared"

/*
 * Loam Combobox: a field pill that opens a searchable card.
 * Trigger and search box are both single-line fields, so both wear the shared
 * field recipe on the control tier. The list floats on the card squircle with
 * the large shadow, and every row is a menu pill.
 */

/** One choice in a Combobox. */
export interface ComboboxOption {
  /** The stored value. */
  value: string
  /** The text shown in the list and in the closed trigger. */
  label: string
  disabled?: boolean
}

/** Props for the Loam combobox. */
export interface ComboboxProps {
  /** The choices to offer. */
  options: ComboboxOption[]
  /** Chosen value when you drive the control yourself. */
  value?: string
  /** Chosen value the control starts with when it drives itself. */
  defaultValue?: string
  /** Runs on every pick. An empty string means the pick was cleared. */
  onValueChange?: (value: string) => void
  placeholder?: string
  searchPlaceholder?: string
  /** Shown when the search matches nothing. */
  emptyMessage?: string
  disabled?: boolean
  className?: string
}

/** A select you can type into: pick one value from a filtered list. */
function Combobox({
  options,
  value,
  defaultValue,
  onValueChange,
  placeholder = "Select an option",
  searchPlaceholder = "Search",
  emptyMessage = "Nothing found.",
  disabled,
  className,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState("")
  const [internal, setInternal] = React.useState(defaultValue ?? "")
  const selected = value ?? internal

  const matches = options.filter(option =>
    option.label.toLowerCase().includes(query.trim().toLowerCase())
  )
  const selectedLabel = options.find(option => option.value === selected)?.label

  const pick = (optionValue: string) => {
    const next = optionValue === selected ? "" : optionValue
    if (value === undefined) {
      setInternal(next)
    }
    onValueChange?.(next)
    setOpen(false)
    setQuery("")
  }

  return (
    <PopoverPrimitive.Root
      open={open}
      onOpenChange={nextOpen => {
        setOpen(nextOpen)
        if (!nextOpen) {
          setQuery("")
        }
      }}
    >
      <PopoverPrimitive.Trigger
        data-slot="combobox-trigger"
        role="combobox"
        aria-expanded={open}
        disabled={disabled}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "cursor-pointer justify-between gap-2 text-left",
          className
        )}
      >
        <span
          className={cn(
            "min-w-0 truncate",
            !selectedLabel && "text-muted-foreground"
          )}
        >
          {selectedLabel ?? placeholder}
        </span>
        <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" />
      </PopoverPrimitive.Trigger>

      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          data-slot="combobox-content"
          align="start"
          sideOffset={6}
          className={cn(
            floatingSurfaceBase,
            "z-50 w-[var(--radix-popover-trigger-width)] overflow-hidden p-1.5",
            "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          )}
        >
          <div data-slot="combobox-search" className="relative p-1">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <input
              value={query}
              onChange={event => setQuery(event.target.value)}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              className={cn(formFieldBase, formFieldSingleLine, "h-9 pl-10")}
            />
          </div>

          <div
            role="listbox"
            data-slot="combobox-list"
            className="mt-1 flex max-h-60 flex-col overflow-y-auto"
          >
            {matches.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                {emptyMessage}
              </p>
            ) : (
              matches.map(option => (
                <button
                  key={option.value}
                  type="button"
                  role="option"
                  aria-selected={option.value === selected}
                  disabled={option.disabled}
                  data-slot="combobox-item"
                  data-disabled={option.disabled ? "" : undefined}
                  onClick={() => pick(option.value)}
                  className={cn(
                    menuItemBase,
                    pressSpring,
                    "w-full cursor-pointer justify-between text-left hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <span className="truncate">{option.label}</span>
                  {option.value === selected && (
                    <Check className="size-4" strokeWidth={3} />
                  )}
                </button>
              ))
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}

export { Combobox }
