import * as React from "react"
import { Menu as MenuPrimitive } from "@base-ui/react/menu"
import { Menubar as MenubarPrimitive } from "@base-ui/react/menubar"
import { Check, ChevronRight, Circle } from "lucide-react"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase, menuItemBase, menuItemHighlight, pressSpring } from "./_shared"

/*
 * Loam Menubar: a pill bar that drops floating menus.
 *
 * The bar itself is a control, so it takes the full pill radius, and each
 * trigger is a smaller pill inside it. The menus it opens are the card radius
 * with the soft large float, the same paper as every other floating surface.
 */

/** A menubar row: the shared pill recipe plus icon sizing. */
const menubarRow = cn(
  menuItemBase,
  menuItemHighlight,
  "focus:outline-none",
  "[&_svg]:pointer-events-none [&_svg]:shrink-0",
  "[&_svg:not([class*='size-'])]:size-4",
  "[&_svg:not([class*='text-'])]:text-muted-foreground"
)

/** The floating surface shared by every menu the bar drops. */
const menubarSurface = cn(
  floatingSurfaceBase,
  "origin-(--transform-origin) overflow-hidden p-1.5 outline-none",
  "transition-[opacity,scale] duration-fast ease-out",
  "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
  "data-[ending-style]:scale-95 data-[ending-style]:opacity-0"
)

/** Keeps the Radix-shaped `onSelect` callback on a menu row. */
interface RowSelectProps {
  /** Fires when the row is activated by pointer or keyboard. */
  onSelect?: (event: Event) => void
}

/** The pill bar that holds the menus. */
function Menubar({
  className,
  ...props
}: React.ComponentProps<typeof MenubarPrimitive>) {
  return (
    <MenubarPrimitive
      data-slot="menubar"
      className={cn(
        "flex items-center gap-1 p-1.5",
        "rounded-[var(--radius-control)] border border-border bg-card",
        "[box-shadow:var(--shadow-2xs)]",
        className
      )}
      {...props}
    />
  )
}

/**
 * One menu inside the bar.
 *
 * Base UI has no Menubar-specific menu part: a plain `Menu.Root` inside the
 * bar joins it, so this export keeps the Radix name over that root.
 */
function MenubarMenu({
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Root>) {
  return <MenuPrimitive.Root {...props} />
}

/** Groups related rows so screen readers announce them together. */
function MenubarGroup({
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Group>) {
  return <MenuPrimitive.Group data-slot="menubar-group" {...props} />
}

/**
 * Renders the menu into a portal at the end of the body.
 *
 * Base UI's portal takes no arbitrary DOM props, so this one carries no
 * data-slot where the Radix copy has one.
 */
function MenubarPortal({
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Portal>) {
  return <MenuPrimitive.Portal {...props} />
}

/** Wraps the radio rows and owns the selected value. */
function MenubarRadioGroup({
  ...props
}: React.ComponentProps<typeof MenuPrimitive.RadioGroup>) {
  return <MenuPrimitive.RadioGroup data-slot="menubar-radio-group" {...props} />
}

/**
 * A top-level pill in the bar that opens its menu.
 *
 * Base UI marks the open trigger with `data-popup-open` where Radix writes
 * `data-state="open"`.
 */
function MenubarTrigger({
  className,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Trigger>) {
  return (
    <MenuPrimitive.Trigger
      data-slot="menubar-trigger"
      className={cn(
        "flex select-none items-center px-4 py-1.5 text-sm font-semibold",
        "rounded-[var(--radius-control)] cursor-pointer text-foreground",
        "transition-[transform,background-color,color] duration-fast ease-out",
        "hover:bg-accent hover:text-accent-foreground",
        "focus-visible:bg-accent focus-visible:text-accent-foreground focus-visible:outline-none",
        "data-[popup-open]:bg-accent data-[popup-open]:text-accent-foreground",
        pressSpring,
        className
      )}
      {...props}
    />
  )
}

/**
 * The floating menu surface dropped by a trigger.
 *
 * Base UI splits Radix's Content into a Positioner that places the surface and
 * a Popup that is the surface.
 */
function MenubarContent({
  className,
  align = "start",
  alignOffset = -4,
  sideOffset = 8,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Popup> & {
  /** Where the surface lines up against its trigger. */
  align?: "start" | "center" | "end"
  /** Nudge along the alignment axis, in pixels. */
  alignOffset?: number
  /** Gap in pixels between the trigger and the surface. */
  sideOffset?: number
}) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Positioner
        align={align}
        alignOffset={alignOffset}
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <MenuPrimitive.Popup
          data-slot="menubar-content"
          className={cn(menubarSurface, "min-w-48", className)}
          {...props}
        />
      </MenuPrimitive.Positioner>
    </MenuPrimitive.Portal>
  )
}

/**
 * A single menu row, optionally the destructive one.
 *
 * Base UI activates a row through `onClick` and marks the hovered row with
 * `data-highlighted`, so this keeps the Radix-shaped `onSelect` prop and the
 * warm hover targets that attribute.
 */
function MenubarItem({
  className,
  inset,
  variant = "default",
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Item> &
  RowSelectProps & {
    /** Indent the row to line up with rows that carry an indicator. */
    inset?: boolean
    /** Paint the row in the red triad, for a row that removes something. */
    variant?: "default" | "destructive"
  }) {
  return (
    <MenuPrimitive.Item
      data-slot="menubar-item"
      data-inset={inset}
      data-variant={variant}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      className={cn(
        menubarRow,
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
function MenubarCheckboxItem({
  className,
  children,
  checked,
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.CheckboxItem> & RowSelectProps) {
  return (
    <MenuPrimitive.CheckboxItem
      data-slot="menubar-checkbox-item"
      className={cn(menubarRow, "pr-3 pl-9", className)}
      checked={checked}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      {...props}
    >
      <span className="pointer-events-none absolute left-3 flex size-3.5 items-center justify-center">
        <MenuPrimitive.CheckboxItemIndicator>
          <Check className="size-4" />
        </MenuPrimitive.CheckboxItemIndicator>
      </span>
      {children}
    </MenuPrimitive.CheckboxItem>
  )
}

/** One choice in a radio group, marked by a dot. */
function MenubarRadioItem({
  className,
  children,
  onSelect,
  onClick,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.RadioItem> & RowSelectProps) {
  return (
    <MenuPrimitive.RadioItem
      data-slot="menubar-radio-item"
      className={cn(menubarRow, "pr-3 pl-9", className)}
      onClick={(event) => {
        onSelect?.(event.nativeEvent)
        onClick?.(event)
      }}
      {...props}
    >
      <span className="pointer-events-none absolute left-3 flex size-3.5 items-center justify-center">
        <MenuPrimitive.RadioItemIndicator>
          <Circle className="size-2 fill-current" />
        </MenuPrimitive.RadioItemIndicator>
      </span>
      {children}
    </MenuPrimitive.RadioItem>
  )
}

/**
 * A non-interactive heading over a group of rows.
 *
 * Base UI names this part GroupLabel, so this export keeps the Radix name.
 */
function MenubarLabel({
  className,
  inset,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.GroupLabel> & {
  /** Indent the label to line up with rows that carry an indicator. */
  inset?: boolean
}) {
  return (
    <MenuPrimitive.GroupLabel
      data-slot="menubar-label"
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
function MenubarSeparator({
  className,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Separator>) {
  return (
    <MenuPrimitive.Separator
      data-slot="menubar-separator"
      className={cn("-mx-1.5 my-1.5 h-px bg-border", className)}
      {...props}
    />
  )
}

/** The trailing keyboard hint on a row. */
function MenubarShortcut({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="menubar-shortcut"
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
function MenubarSub({
  ...props
}: React.ComponentProps<typeof MenuPrimitive.SubmenuRoot>) {
  return <MenuPrimitive.SubmenuRoot {...props} />
}

/** The row that opens a submenu, with a trailing chevron. */
function MenubarSubTrigger({
  className,
  inset,
  children,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.SubmenuTrigger> & {
  /** Indent the row to line up with rows that carry an indicator. */
  inset?: boolean
}) {
  return (
    <MenuPrimitive.SubmenuTrigger
      data-slot="menubar-sub-trigger"
      data-inset={inset}
      className={cn(
        menubarRow,
        "data-[inset]:pl-9",
        "data-[popup-open]:bg-accent data-[popup-open]:text-accent-foreground",
        className
      )}
      {...props}
    >
      {children}
      <ChevronRight className="ml-auto size-4" />
    </MenuPrimitive.SubmenuTrigger>
  )
}

/** The submenu surface, same paper as the parent menu. */
function MenubarSubContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentProps<typeof MenuPrimitive.Popup> & {
  /** Gap in pixels between the parent row and the submenu. */
  sideOffset?: number
}) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Positioner
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <MenuPrimitive.Popup
          data-slot="menubar-sub-content"
          className={cn(menubarSurface, "min-w-40", className)}
          {...props}
        />
      </MenuPrimitive.Positioner>
    </MenuPrimitive.Portal>
  )
}

export {
  Menubar,
  MenubarPortal,
  MenubarMenu,
  MenubarTrigger,
  MenubarContent,
  MenubarGroup,
  MenubarSeparator,
  MenubarLabel,
  MenubarItem,
  MenubarShortcut,
  MenubarCheckboxItem,
  MenubarRadioGroup,
  MenubarRadioItem,
  MenubarSub,
  MenubarSubTrigger,
  MenubarSubContent,
}
