"use client"

import * as React from "react"
import { Menu as DropdownMenuPrimitive } from "@base-ui/react/menu"
import { Check, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase, menuItemBase, menuItemHighlight } from "./_shared"

/*
 * Loam DropdownMenu: a floating surface holding pill rows.
 *
 * The menu is the card radius (1.5rem) with the soft large float, and every
 * row inside it is a full pill from menuItemBase. Two tiers of the radius
 * scale in one component, which is how Loam signals container against control.
 */

/** A menu row: the shared pill recipe plus icon sizing. */
const dropdownMenuRow = cn(
  menuItemBase,
  menuItemHighlight,
  "focus:outline-none",
  "[&_svg]:pointer-events-none [&_svg]:shrink-0",
  "[&_svg:not([class*='size-'])]:size-4",
  "[&_svg:not([class*='text-'])]:text-muted-foreground"
)

/** The floating surface shared by the menu and its submenus. */
const dropdownMenuSurface = cn(
  floatingSurfaceBase,
  "min-w-40 origin-(--transform-origin)",
  "overflow-x-hidden overflow-y-auto p-1.5 outline-none",
  "transition-[opacity,scale] duration-fast ease-out",
  "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
  "data-[ending-style]:scale-95 data-[ending-style]:opacity-0"
)

/** Keeps the Radix-shaped `onSelect` callback on a menu row. */
interface RowSelectProps {
  /** Fires when the row is activated by pointer or keyboard. */
  onSelect?: (event: Event) => void
}

/** Root of the dropdown menu. */
function DropdownMenu({
  modal = false,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Root>) {
  return <DropdownMenuPrimitive.Root modal={modal} {...props} />
}

/**
 * Renders the menu into a portal at the end of the body.
 *
 * Base UI's portal takes no arbitrary DOM props, so this one carries no
 * data-slot where the Radix copy has one.
 */
function DropdownMenuPortal({
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Portal>) {
  return <DropdownMenuPrimitive.Portal {...props} />
}

/** The control that opens the menu. */
function DropdownMenuTrigger({
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Trigger>) {
  return (
    <DropdownMenuPrimitive.Trigger
      data-slot="dropdown-menu-trigger"
      {...props}
    />
  )
}

/**
 * The floating menu surface.
 *
 * Base UI splits Radix's Content into a Positioner that places the surface and
 * a Popup that is the surface, and publishes the room it has as
 * `--available-height`.
 */
function DropdownMenuContent({
  className,
  sideOffset = 8,
  align,
  alignOffset,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Popup> & {
  /** Gap in pixels between the trigger and the surface. */
  sideOffset?: number
  /** Where the surface lines up against its trigger. */
  align?: "start" | "center" | "end"
  /** Nudge along the alignment axis, in pixels. */
  alignOffset?: number
}) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Positioner
        sideOffset={sideOffset}
        align={align}
        alignOffset={alignOffset}
        className="z-50 outline-none"
      >
        <DropdownMenuPrimitive.Popup
          data-slot="dropdown-menu-content"
          className={cn(
            dropdownMenuSurface,
            "max-h-(--available-height)",
            className
          )}
          {...props}
        />
      </DropdownMenuPrimitive.Positioner>
    </DropdownMenuPrimitive.Portal>
  )
}

/** Groups related rows so screen readers announce them together. */
function DropdownMenuGroup({
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Group>) {
  return (
    <DropdownMenuPrimitive.Group data-slot="dropdown-menu-group" {...props} />
  )
}

/**
 * A single menu row, optionally the destructive one.
 *
 * Base UI activates a row through `onClick` and marks the hovered row with
 * `data-highlighted`, so this keeps the Radix-shaped `onSelect` prop and the
 * warm hover targets that attribute.
 */
function DropdownMenuItem({
  className,
  inset,
  variant = "default",
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Item> &
  RowSelectProps & {
    /** Indent the row to line up with rows that carry an indicator. */
    inset?: boolean
    /** Paint the row in the red triad, for a row that removes something. */
    variant?: "default" | "destructive"
  }) {
  return (
    <DropdownMenuPrimitive.Item
      data-slot="dropdown-menu-item"
      data-inset={inset}
      data-variant={variant}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      className={cn(
        dropdownMenuRow,
        "data-[inset]:pl-9",
        "data-[variant=destructive]:text-destructive",
        "data-[variant=destructive]:data-[highlighted]:bg-pop-red-surface",
        "data-[variant=destructive]:data-[highlighted]:text-pop-red-ink",
        "data-[variant=destructive]:*:[svg]:!text-destructive",
        className
      )}
      {...props}
    />
  )
}

/** A menu row that toggles, with the check in the leading slot. */
function DropdownMenuCheckboxItem({
  className,
  children,
  checked,
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.CheckboxItem> &
  RowSelectProps) {
  return (
    <DropdownMenuPrimitive.CheckboxItem
      data-slot="dropdown-menu-checkbox-item"
      className={cn(dropdownMenuRow, "pr-3 pl-9", className)}
      checked={checked}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      {...props}
    >
      <span className="pointer-events-none absolute left-3 flex size-3.5 items-center justify-center">
        <DropdownMenuPrimitive.CheckboxItemIndicator>
          <Check className="size-4" />
        </DropdownMenuPrimitive.CheckboxItemIndicator>
      </span>
      {children}
    </DropdownMenuPrimitive.CheckboxItem>
  )
}

/** Wraps the radio rows and owns the selected value. */
function DropdownMenuRadioGroup({
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.RadioGroup>) {
  return (
    <DropdownMenuPrimitive.RadioGroup
      data-slot="dropdown-menu-radio-group"
      {...props}
    />
  )
}

/** One choice in a radio group, marked by a dot. */
function DropdownMenuRadioItem({
  className,
  children,
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.RadioItem> &
  RowSelectProps) {
  return (
    <DropdownMenuPrimitive.RadioItem
      data-slot="dropdown-menu-radio-item"
      className={cn(dropdownMenuRow, "pr-3 pl-9", className)}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      {...props}
    >
      <span className="pointer-events-none absolute left-3 flex size-3.5 items-center justify-center">
        <DropdownMenuPrimitive.RadioItemIndicator>
          <span className="size-2 rounded-[var(--radius-control)] bg-current" />
        </DropdownMenuPrimitive.RadioItemIndicator>
      </span>
      {children}
    </DropdownMenuPrimitive.RadioItem>
  )
}

/**
 * A non-interactive heading over a group of rows.
 *
 * Base UI names this part GroupLabel, so this export keeps the Radix name.
 */
function DropdownMenuLabel({
  className,
  inset,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.GroupLabel> & {
  /** Indent the label to line up with rows that carry an indicator. */
  inset?: boolean
}) {
  return (
    <DropdownMenuPrimitive.GroupLabel
      data-slot="dropdown-menu-label"
      data-inset={inset}
      className={cn(
        "px-3 py-1.5 text-xs font-semibold text-muted-foreground data-[inset]:pl-9",
        className
      )}
      {...props}
    />
  )
}

/** A warm hairline between groups of rows. */
function DropdownMenuSeparator({
  className,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator
      data-slot="dropdown-menu-separator"
      className={cn("-mx-1.5 my-1.5 h-px bg-border", className)}
      {...props}
    />
  )
}

/** The trailing keyboard hint on a row. */
function DropdownMenuShortcut({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="dropdown-menu-shortcut"
      className={cn(
        "ml-auto font-mono text-xs tracking-widest text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/**
 * Root of a nested submenu.
 *
 * Base UI names this part SubmenuRoot, so this export keeps the Radix name.
 */
function DropdownMenuSub({
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.SubmenuRoot>) {
  return <DropdownMenuPrimitive.SubmenuRoot {...props} />
}

/**
 * The row that opens a submenu, with a trailing chevron.
 *
 * Base UI marks the open row with `data-popup-open` where Radix writes
 * `data-state="open"`.
 */
function DropdownMenuSubTrigger({
  className,
  inset,
  children,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.SubmenuTrigger> & {
  /** Indent the row to line up with rows that carry an indicator. */
  inset?: boolean
}) {
  return (
    <DropdownMenuPrimitive.SubmenuTrigger
      data-slot="dropdown-menu-sub-trigger"
      data-inset={inset}
      className={cn(
        dropdownMenuRow,
        "data-[inset]:pl-9",
        "data-[popup-open]:bg-accent data-[popup-open]:text-accent-foreground",
        className
      )}
      {...props}
    >
      {children}
      <ChevronRight className="ml-auto size-4" />
    </DropdownMenuPrimitive.SubmenuTrigger>
  )
}

/** The submenu surface, same paper as the parent menu. */
function DropdownMenuSubContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentProps<typeof DropdownMenuPrimitive.Popup> & {
  /** Gap in pixels between the parent row and the submenu. */
  sideOffset?: number
}) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Positioner
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <DropdownMenuPrimitive.Popup
          data-slot="dropdown-menu-sub-content"
          className={cn(dropdownMenuSurface, "overflow-hidden", className)}
          {...props}
        />
      </DropdownMenuPrimitive.Positioner>
    </DropdownMenuPrimitive.Portal>
  )
}

export {
  DropdownMenu,
  DropdownMenuPortal,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
}
