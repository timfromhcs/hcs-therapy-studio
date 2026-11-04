"use client"

import * as React from "react"
import { Select as SelectPrimitive } from "@base-ui/react/select"
import { Check, ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  floatingSurfaceBase,
  formFieldBase,
  formFieldSingleLine,
  menuItemBase,
  menuItemHighlight,
} from "./_shared"

/*
 * Loam Select: a field pill that opens a card.
 * The trigger is a single-line field, so it takes the control tier and the
 * shared field recipe. The list floats on the card squircle with the large
 * shadow, and its rows are pills like every other menu row in Loam.
 */

/** Select root. Holds the open state and the chosen value. */
function Select<Value, Multiple extends boolean | undefined = false>(
  props: SelectPrimitive.Root.Props<Value, Multiple>
) {
  return <SelectPrimitive.Root {...props} />
}

/** Groups related options under one label. */
function SelectGroup({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Group>) {
  return <SelectPrimitive.Group data-slot="select-group" {...props} />
}

/** Shows the chosen option, or the placeholder while nothing is chosen. */
function SelectValue({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Value>) {
  return <SelectPrimitive.Value data-slot="select-value" {...props} />
}

/** The closed select: a Loam field pill with a chevron. */
function SelectTrigger({
  className,
  size = "default",
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Trigger> & {
  /** `sm` shortens the pill for dense toolbars. */
  size?: "sm" | "default"
}) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      data-size={size}
      className={cn(
        formFieldBase,
        formFieldSingleLine,
        "cursor-pointer justify-between gap-2 whitespace-nowrap text-left",
        "data-[size=sm]:h-8 data-[size=sm]:px-3 data-[size=sm]:text-xs",
        "data-[placeholder]:text-muted-foreground",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        "*:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2",
        className
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon>
        <ChevronDown className="size-4 text-muted-foreground" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

/**
 * The floating option list on the Loam card squircle.
 *
 * Base UI splits Radix's Content into a Positioner, a Popup and a List, and
 * publishes the room it has as `--available-height`, so the max height reads
 * that variable instead of the Radix one.
 */
function SelectContent({
  className,
  children,
  sideOffset = 8,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Popup> & {
  /** Gap in pixels between the trigger and the list. */
  sideOffset?: number
}) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Positioner
        sideOffset={sideOffset}
        className="z-50 select-none outline-none"
      >
        <SelectPrimitive.Popup
          data-slot="select-content"
          className={cn(
            floatingSurfaceBase,
            "relative min-w-32 origin-(--transform-origin) overflow-hidden",
            "transition-[opacity,scale] duration-fast ease-out",
            "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
            "data-[ending-style]:scale-95 data-[ending-style]:opacity-0",
            className
          )}
          {...props}
        >
          <SelectScrollUpButton />
          <SelectPrimitive.List className="max-h-(--available-height) w-full min-w-(--anchor-width) scroll-my-1 overflow-y-auto p-1.5">
            {children}
          </SelectPrimitive.List>
          <SelectScrollDownButton />
        </SelectPrimitive.Popup>
      </SelectPrimitive.Positioner>
    </SelectPrimitive.Portal>
  )
}

/**
 * Caption above a group of options.
 *
 * Base UI keeps `Select.Label` for the control's own caption and names the
 * in-list heading `Select.GroupLabel`, which is what Radix means here.
 */
function SelectLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.GroupLabel>) {
  return (
    <SelectPrimitive.GroupLabel
      data-slot="select-label"
      className={cn(
        "px-3 py-1.5 text-xs font-semibold text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/** One selectable option, on the shared Loam menu pill. */
function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        menuItemBase,
        menuItemHighlight,
        "w-full pr-9",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <span className="absolute right-3 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-4" strokeWidth={3} />
        </SelectPrimitive.ItemIndicator>
      </span>
    </SelectPrimitive.Item>
  )
}

/** Hairline rule between option groups. */
function SelectSeparator({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator
      data-slot="select-separator"
      className={cn(
        "pointer-events-none -mx-1 my-1.5 h-px bg-border",
        className
      )}
      {...props}
    />
  )
}

/**
 * Scrolls a long list up.
 *
 * Base UI names this part ScrollUpArrow, so this export keeps the Radix name.
 */
function SelectScrollUpButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollUpArrow>) {
  return (
    <SelectPrimitive.ScrollUpArrow
      data-slot="select-scroll-up-button"
      className={cn(
        "flex cursor-default items-center justify-center py-1 text-muted-foreground",
        className
      )}
      {...props}
    >
      <ChevronUp className="size-4" />
    </SelectPrimitive.ScrollUpArrow>
  )
}

/**
 * Scrolls a long list down.
 *
 * Base UI names this part ScrollDownArrow, so this export keeps the Radix name.
 */
function SelectScrollDownButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollDownArrow>) {
  return (
    <SelectPrimitive.ScrollDownArrow
      data-slot="select-scroll-down-button"
      className={cn(
        "flex cursor-default items-center justify-center py-1 text-muted-foreground",
        className
      )}
      {...props}
    >
      <ChevronDown className="size-4" />
    </SelectPrimitive.ScrollDownArrow>
  )
}

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
}
