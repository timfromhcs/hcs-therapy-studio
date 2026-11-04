import * as React from "react"
import { Toggle as TogglePrimitive } from "@base-ui/react/toggle"
import { ToggleGroup as ToggleGroupPrimitive } from "@base-ui/react/toggle-group"
import { type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { toggleVariants } from "./toggle"

/*
 * Loam ToggleGroup: separate pills on a muted rail.
 *
 * Loam never welds segments into one bar, because a control is always a full
 * pill. The group is the rail at the control tier with inner padding, and each
 * item keeps its own pill shape. The rail holds no shadow, so the pressed pill
 * is the only thing with a fill.
 */

const ToggleGroupContext = React.createContext<
  VariantProps<typeof toggleVariants>
>({
  size: "default",
  variant: "default",
})

/** Props for the toggle rail, keeping Radix's `type` and scalar `value`. */
export interface ToggleGroupProps
  extends Omit<
      React.ComponentPropsWithoutRef<typeof ToggleGroupPrimitive>,
      "value" | "defaultValue" | "onValueChange" | "multiple" | "className"
    >,
    VariantProps<typeof toggleVariants> {
  /** Extra classes for the rail. */
  className?: string
  /** `single` holds one pill down, `multiple` holds several. */
  type?: "single" | "multiple"
  /** The pressed pill, or pills when `type` is `multiple`. */
  value?: string | string[]
  /** The starting pressed pill when the group is uncontrolled. */
  defaultValue?: string | string[]
  /** Fires with a string for `single` and an array for `multiple`. */
  onValueChange?: (value: string | string[]) => void
}

function toArray(value: string | string[] | undefined) {
  if (value === undefined) return undefined
  return Array.isArray(value) ? value : [value]
}

/**
 * The rail that groups toggle pills and shares their variant and size.
 *
 * Base UI always holds the pressed values in an array and takes a `multiple`
 * boolean, so this wrapper keeps Radix's `type` plus scalar `value` and maps
 * both onto the Base UI shape.
 */
function ToggleGroup({
  className,
  variant,
  size,
  children,
  type = "single",
  value,
  defaultValue,
  onValueChange,
  ...props
}: ToggleGroupProps) {
  const multiple = type === "multiple"

  return (
    <ToggleGroupPrimitive
      data-slot="toggle-group"
      data-variant={variant}
      data-size={size}
      multiple={multiple}
      value={toArray(value)}
      defaultValue={toArray(defaultValue)}
      onValueChange={(next) => {
        const list = next.map(String)
        onValueChange?.(multiple ? list : (list[0] ?? ""))
      }}
      className={cn(
        "flex w-fit items-center gap-1",
        "rounded-[var(--radius-control)] bg-muted p-1",
        "data-[variant=outline]:bg-transparent data-[variant=outline]:p-0 data-[variant=outline]:gap-2",
        className
      )}
      {...props}
    >
      <ToggleGroupContext.Provider value={{ variant, size }}>
        {children}
      </ToggleGroupContext.Provider>
    </ToggleGroupPrimitive>
  )
}

/**
 * One pill in the group. Pressed, it takes the primary button's flat fill.
 *
 * Base UI has no group-specific item: a plain Toggle inside the group joins
 * it, so this export keeps the Radix name and renders that Toggle.
 */
function ToggleGroupItem({
  className,
  children,
  variant,
  size,
  ...props
}: React.ComponentProps<typeof TogglePrimitive> &
  VariantProps<typeof toggleVariants>) {
  const context = React.useContext(ToggleGroupContext)

  return (
    <TogglePrimitive
      data-slot="toggle-group-item"
      data-variant={context.variant ?? variant}
      data-size={context.size ?? size}
      className={cn(
        toggleVariants({
          variant: context.variant ?? variant,
          size: context.size ?? size,
        }),
        "min-w-0 shrink-0 focus-visible:z-10",
        className
      )}
      {...props}
    >
      {children}
    </TogglePrimitive>
  )
}

export { ToggleGroup, ToggleGroupItem }
