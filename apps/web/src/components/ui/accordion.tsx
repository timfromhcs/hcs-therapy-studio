import * as React from "react"
import { Accordion as AccordionPrimitive } from "@base-ui/react/accordion"
import { ChevronDownIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/*
 * Loam Accordion: each item is a card, not a table row.
 *
 * An item sits at the card tier (1.5rem) with a warm hairline and the soft
 * card float, so a list of sections reads as a stack of paper. The trigger
 * fills the top of that card and carries no rim or shadow of its own, because
 * the shape belongs to the outer surface.
 */

/** Props for the accordion root, keeping Radix's `type` and scalar `value`. */
export interface AccordionProps
  extends Omit<
    React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Root>,
    "value" | "defaultValue" | "onValueChange" | "multiple" | "className"
  > {
  /** Extra classes for the stack. */
  className?: string
  /** `single` opens one section at a time, `multiple` opens several. */
  type?: "single" | "multiple"
  /** Accepted for Radix parity. Base UI always lets the open section close. */
  collapsible?: boolean
  /** The open section, or sections when `type` is `multiple`. */
  value?: string | string[]
  /** The starting open section when the accordion is uncontrolled. */
  defaultValue?: string | string[]
  /** Fires with a string for `single` and an array for `multiple`. */
  onValueChange?: (value: string | string[]) => void
}

function toArray(value: string | string[] | undefined) {
  if (value === undefined) return undefined
  return Array.isArray(value) ? value : [value]
}

/**
 * The accordion root: a stack of independently opening card sections.
 *
 * Base UI always holds the open sections in an array and takes a `multiple`
 * boolean, so this wrapper keeps Radix's `type` plus scalar `value` and maps
 * both onto the Base UI shape.
 */
function Accordion({
  className,
  type = "single",
  collapsible: _collapsible,
  value,
  defaultValue,
  onValueChange,
  ...props
}: AccordionProps) {
  const multiple = type === "multiple"

  return (
    <AccordionPrimitive.Root
      data-slot="accordion"
      multiple={multiple}
      value={toArray(value)}
      defaultValue={toArray(defaultValue)}
      onValueChange={(next: readonly (string | number)[]) => {
        const list = next.map(String)
        onValueChange?.(multiple ? list : (list[0] ?? ""))
      }}
      className={cn("flex w-full flex-col gap-3", className)}
      {...props}
    />
  )
}

/** One section of the accordion, styled as a white card squircle. */
function AccordionItem({
  className,
  ...props
}: React.ComponentProps<typeof AccordionPrimitive.Item>) {
  return (
    <AccordionPrimitive.Item
      data-slot="accordion-item"
      className={cn(
        "overflow-hidden rounded-[var(--radius-card)] border border-border bg-card text-card-foreground",
        "[box-shadow:var(--shadow-sm)]",
        className
      )}
      {...props}
    />
  )
}

/**
 * The row that opens a section, with a chevron that turns as it opens.
 *
 * Base UI marks the open trigger with `data-panel-open` where Radix writes
 * `data-state="open"`, so the chevron rule targets that attribute.
 */
function AccordionTrigger({
  className,
  children,
  ...props
}: React.ComponentProps<typeof AccordionPrimitive.Trigger>) {
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger
        data-slot="accordion-trigger"
        className={cn(
          "flex flex-1 items-center justify-between gap-4 px-6 py-5",
          "text-left text-sm font-semibold text-foreground",
          "cursor-pointer select-none rounded-[inherit]",
          "transition-colors duration-fast ease-out outline-none",
          "hover:bg-accent hover:text-accent-foreground",
          "focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:pointer-events-none disabled:opacity-50",
          "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
          "[&[data-panel-open]>svg]:rotate-180",
          className
        )}
        {...props}
      >
        {children}
        <ChevronDownIcon
          aria-hidden="true"
          className="pointer-events-none size-4 shrink-0 text-muted-foreground transition-transform duration-base ease-out"
        />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  )
}

/**
 * The body of a section, which slides open under its trigger.
 *
 * Base UI publishes the measured height as `--accordion-panel-height` and
 * drives the open and shut with a height transition, so this replaces the
 * Radix keyframe pair with that transition and keeps the same motion.
 */
function AccordionContent({
  className,
  children,
  ...props
}: React.ComponentProps<typeof AccordionPrimitive.Panel>) {
  return (
    <AccordionPrimitive.Panel
      data-slot="accordion-content"
      className={cn(
        "h-[var(--accordion-panel-height)] overflow-hidden text-sm text-muted-foreground",
        "transition-[height] duration-base ease-out",
        "data-[starting-style]:h-0 data-[ending-style]:h-0"
      )}
      {...props}
    >
      <div className={cn("px-6 pt-0 pb-5", className)}>{children}</div>
    </AccordionPrimitive.Panel>
  )
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
