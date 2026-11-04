import * as React from "react"

import { cn } from "@/lib/utils"
import { Checkbox } from "./checkbox"
import { Label } from "./label"

/*
 * Loam CheckboxGroup: several checkboxes that share one value list.
 * The group is layout only, so it draws no surface and takes no radius tier.
 * Each row reuses the Loam Checkbox, so a ticked box keeps the flat near-black
 * fill of the primary Button.
 */

type CheckboxGroupContextValue = {
  value: string[]
  toggle: (itemValue: string) => void
  disabled?: boolean
  name?: string
}

const CheckboxGroupContext =
  React.createContext<CheckboxGroupContextValue | null>(null)

/** Props for the Loam checkbox group. */
export interface CheckboxGroupProps
  extends Omit<React.ComponentProps<"div">, "onChange"> {
  /** Ticked values when you drive the group yourself. */
  value?: string[]
  /** Ticked values the group starts with when it drives itself. */
  defaultValue?: string[]
  /** Runs after every tick or untick, with the full new list. */
  onValueChange?: (value: string[]) => void
  /** Form field name shared by every box in the group. */
  name?: string
  disabled?: boolean
}

/** Holds the shared value list for the boxes nested inside it. */
function CheckboxGroup({
  className,
  value,
  defaultValue,
  onValueChange,
  name,
  disabled,
  children,
  ...props
}: CheckboxGroupProps) {
  const [internal, setInternal] = React.useState<string[]>(defaultValue ?? [])
  const selected = value ?? internal

  const toggle = React.useCallback(
    (itemValue: string) => {
      const next = selected.includes(itemValue)
        ? selected.filter(item => item !== itemValue)
        : [...selected, itemValue]
      if (value === undefined) {
        setInternal(next)
      }
      onValueChange?.(next)
    },
    [onValueChange, selected, value]
  )

  return (
    <CheckboxGroupContext.Provider
      value={{ value: selected, toggle, disabled, name }}
    >
      <div
        data-slot="checkbox-group"
        role="group"
        className={cn("flex flex-col gap-3", className)}
        {...props}
      >
        {children}
      </div>
    </CheckboxGroupContext.Provider>
  )
}

/** One labelled box in the group. Reads its state from the group. */
function CheckboxGroupItem({
  className,
  value: itemValue,
  disabled,
  children,
  ...props
}: Omit<React.ComponentProps<"div">, "onChange"> & {
  /** The value this box contributes to the group. */
  value: string
  disabled?: boolean
}) {
  const group = React.useContext(CheckboxGroupContext)

  if (!group) {
    throw new Error("CheckboxGroupItem should be used within <CheckboxGroup>")
  }

  const id = React.useId()
  const isDisabled = disabled ?? group.disabled

  return (
    <div
      data-slot="checkbox-group-item"
      data-disabled={isDisabled ? "true" : undefined}
      className={cn("group flex items-center gap-3", className)}
      {...props}
    >
      <Checkbox
        id={id}
        name={group.name}
        value={itemValue}
        checked={group.value.includes(itemValue)}
        disabled={isDisabled}
        onCheckedChange={() => group.toggle(itemValue)}
      />
      <Label htmlFor={id} className="font-normal">
        {children}
      </Label>
    </div>
  )
}

export { CheckboxGroup, CheckboxGroupItem }
