import * as React from "react"
import { ContextMenu as ContextMenuPrimitive } from "@base-ui/react/context-menu"
import { Check, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase, menuItemBase, menuItemHighlight } from "./_shared"

/*
 * Loam ContextMenu: the same paper as the dropdown menu.
 *
 * A right-click menu is a floating surface, so it takes the card radius
 * (1.5rem) and the soft large float, with full-pill rows inside it. One
 * treatment for every menu means the system never looks assembled.
 */

/** A context menu row: the shared pill recipe plus icon sizing. */
const contextMenuRow = cn(
  menuItemBase,
  menuItemHighlight,
  "focus:outline-none",
  "[&_svg]:pointer-events-none [&_svg]:shrink-0",
  "[&_svg:not([class*='size-'])]:size-4",
  "[&_svg:not([class*='text-'])]:text-muted-foreground"
)

/** The floating surface shared by the menu and its submenus. */
const contextMenuSurface = cn(
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

/** Root of the context menu. */
function ContextMenu({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Root>) {
  return <ContextMenuPrimitive.Root {...props} />
}

/** The region that opens the menu on right-click or long press. */
function ContextMenuTrigger({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Trigger>) {
  return (
    <ContextMenuPrimitive.Trigger data-slot="context-menu-trigger" {...props} />
  )
}

/** Groups related rows so screen readers announce them together. */
function ContextMenuGroup({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Group>) {
  return (
    <ContextMenuPrimitive.Group data-slot="context-menu-group" {...props} />
  )
}

/**
 * Renders the menu into a portal at the end of the body.
 *
 * Base UI's portal takes no arbitrary DOM props, so this one carries no
 * data-slot where the Radix copy has one.
 */
function ContextMenuPortal({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Portal>) {
  return <ContextMenuPrimitive.Portal {...props} />
}

/**
 * Root of a nested submenu.
 *
 * Base UI names this part SubmenuRoot, so this export keeps the Radix name.
 */
function ContextMenuSub({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.SubmenuRoot>) {
  return <ContextMenuPrimitive.SubmenuRoot {...props} />
}

/** Wraps the radio rows and owns the selected value. */
function ContextMenuRadioGroup({
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.RadioGroup>) {
  return (
    <ContextMenuPrimitive.RadioGroup
      data-slot="context-menu-radio-group"
      {...props}
    />
  )
}

/**
 * The row that opens a submenu, with a trailing chevron.
 *
 * Base UI marks the open row with `data-popup-open` where Radix writes
 * `data-state="open"`.
 */
function ContextMenuSubTrigger({
  className,
  inset,
  children,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.SubmenuTrigger> & {
  /** Indent the row to line up with rows that carry an indicator. */
  inset?: boolean
}) {
  return (
    <ContextMenuPrimitive.SubmenuTrigger
      data-slot="context-menu-sub-trigger"
      data-inset={inset}
      className={cn(
        contextMenuRow,
        "data-[inset]:pl-9",
        "data-[popup-open]:bg-accent data-[popup-open]:text-accent-foreground",
        className
      )}
      {...props}
    >
      {children}
      <ChevronRight className="ml-auto size-4" />
    </ContextMenuPrimitive.SubmenuTrigger>
  )
}

/** The submenu surface, same paper as the parent menu. */
function ContextMenuSubContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Popup> & {
  /** Gap in pixels between the parent row and the submenu. */
  sideOffset?: number
}) {
  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.Positioner
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <ContextMenuPrimitive.Popup
          data-slot="context-menu-sub-content"
          className={cn(contextMenuSurface, "overflow-hidden", className)}
          {...props}
        />
      </ContextMenuPrimitive.Positioner>
    </ContextMenuPrimitive.Portal>
  )
}

/**
 * The floating menu surface.
 *
 * Base UI splits Radix's Content into a Positioner that places the surface and
 * a Popup that is the surface.
 */
function ContextMenuContent({
  className,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Popup>) {
  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.Positioner className="z-50 outline-none">
        <ContextMenuPrimitive.Popup
          data-slot="context-menu-content"
          className={cn(
            contextMenuSurface,
            "max-h-(--available-height)",
            className
          )}
          {...props}
        />
      </ContextMenuPrimitive.Positioner>
    </ContextMenuPrimitive.Portal>
  )
}

/**
 * A single menu row, optionally the destructive one.
 *
 * Base UI activates a row through `onClick` and marks the hovered row with
 * `data-highlighted`, so this keeps the Radix-shaped `onSelect` prop and the
 * warm hover targets that attribute.
 */
function ContextMenuItem({
  className,
  inset,
  variant = "default",
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Item> &
  RowSelectProps & {
    /** Indent the row to line up with rows that carry an indicator. */
    inset?: boolean
    /** Paint the row in the red triad, for a row that removes something. */
    variant?: "default" | "destructive"
  }) {
  return (
    <ContextMenuPrimitive.Item
      data-slot="context-menu-item"
      data-inset={inset}
      data-variant={variant}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      className={cn(
        contextMenuRow,
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
function ContextMenuCheckboxItem({
  className,
  children,
  checked,
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.CheckboxItem> &
  RowSelectProps) {
  return (
    <ContextMenuPrimitive.CheckboxItem
      data-slot="context-menu-checkbox-item"
      className={cn(contextMenuRow, "pr-3 pl-9", className)}
      checked={checked}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      {...props}
    >
      <span className="pointer-events-none absolute left-3 flex size-3.5 items-center justify-center">
        <ContextMenuPrimitive.CheckboxItemIndicator>
          <Check className="size-4" />
        </ContextMenuPrimitive.CheckboxItemIndicator>
      </span>
      {children}
    </ContextMenuPrimitive.CheckboxItem>
  )
}

/** One choice in a radio group, marked by a dot. */
function ContextMenuRadioItem({
  className,
  children,
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.RadioItem> &
  RowSelectProps) {
  return (
    <ContextMenuPrimitive.RadioItem
      data-slot="context-menu-radio-item"
      className={cn(contextMenuRow, "pr-3 pl-9", className)}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      {...props}
    >
      <span className="pointer-events-none absolute left-3 flex size-3.5 items-center justify-center">
        <ContextMenuPrimitive.RadioItemIndicator>
          <span className="size-2 rounded-[var(--radius-control)] bg-current" />
        </ContextMenuPrimitive.RadioItemIndicator>
      </span>
      {children}
    </ContextMenuPrimitive.RadioItem>
  )
}

/**
 * A non-interactive heading over a group of rows.
 *
 * Base UI names this part GroupLabel, so this export keeps the Radix name.
 */
function ContextMenuLabel({
  className,
  inset,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.GroupLabel> & {
  /** Indent the label to line up with rows that carry an indicator. */
  inset?: boolean
}) {
  return (
    <ContextMenuPrimitive.GroupLabel
      data-slot="context-menu-label"
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
function ContextMenuSeparator({
  className,
  ...props
}: React.ComponentProps<typeof ContextMenuPrimitive.Separator>) {
  return (
    <ContextMenuPrimitive.Separator
      data-slot="context-menu-separator"
      className={cn("-mx-1.5 my-1.5 h-px bg-border", className)}
      {...props}
    />
  )
}

/** The trailing keyboard hint on a row. */
function ContextMenuShortcut({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="context-menu-shortcut"
      className={cn(
        "ml-auto font-mono text-xs tracking-widest text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

export {
  ContextMenu,
  ContextMenuTrigger,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuCheckboxItem,
  ContextMenuRadioItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuShortcut,
  ContextMenuGroup,
  ContextMenuPortal,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuRadioGroup,
}
