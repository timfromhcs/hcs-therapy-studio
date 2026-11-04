import * as React from "react"
import { NavigationMenu as NavigationMenuPrimitive } from "@base-ui/react/navigation-menu"
import { cva } from "class-variance-authority"
import { ChevronDownIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase, pressSpring } from "./_shared"

/*
 * Loam NavigationMenu: control-tier pills that drop one card.
 *
 * Each trigger is a full pill like every other Loam control, and the panel it
 * opens is the card squircle (1.5rem) with the soft large float, the same
 * paper as a popover or a menu.
 */

/** The pill styling every top-level trigger and plain nav link shares. */
const navigationMenuTriggerStyle = cva(
  [
    "group inline-flex h-10 w-max items-center justify-center gap-1.5",
    "rounded-[var(--radius-control)] px-4 text-sm font-semibold text-foreground",
    "cursor-pointer select-none no-underline",
    "transition-[transform,background-color,color] duration-fast ease-out outline-none",
    "hover:bg-accent hover:text-accent-foreground",
    "focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50",
    "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
    "data-[popup-open]:bg-accent data-[popup-open]:text-accent-foreground",
    pressSpring,
  ].join(" ")
)

/**
 * The navigation menu root, which renders its own floating panel.
 *
 * Base UI puts the panel in a portal beside the list rather than inside it, so
 * this root renders `NavigationMenuViewport` for you when `viewport` is true.
 */
function NavigationMenu({
  className,
  children,
  viewport = true,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Root> & {
  /** Render the shared floating panel. Turn it off to place your own. */
  viewport?: boolean
}) {
  return (
    <NavigationMenuPrimitive.Root
      data-slot="navigation-menu"
      data-viewport={viewport}
      className={cn(
        "group/navigation-menu relative flex max-w-max flex-1 items-center justify-center",
        className
      )}
      {...props}
    >
      {children}
      {viewport && <NavigationMenuViewport />}
    </NavigationMenuPrimitive.Root>
  )
}

/** The row of top-level pills. */
function NavigationMenuList({
  className,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.List>) {
  return (
    <NavigationMenuPrimitive.List
      data-slot="navigation-menu-list"
      className={cn(
        "group flex flex-1 list-none items-center justify-center gap-1",
        className
      )}
      {...props}
    />
  )
}

/** One entry in the row, holding a trigger and its content. */
function NavigationMenuItem({
  className,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Item>) {
  return (
    <NavigationMenuPrimitive.Item
      data-slot="navigation-menu-item"
      className={cn("relative", className)}
      {...props}
    />
  )
}

/**
 * A top-level pill that opens its panel, with a chevron that turns.
 *
 * Base UI puts the chevron in its own Icon part and marks the open trigger
 * with `data-popup-open` where Radix writes `data-state="open"`.
 */
function NavigationMenuTrigger({
  className,
  children,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Trigger>) {
  return (
    <NavigationMenuPrimitive.Trigger
      data-slot="navigation-menu-trigger"
      className={cn(navigationMenuTriggerStyle(), className)}
      {...props}
    >
      {children}
      <NavigationMenuPrimitive.Icon className="transition-transform duration-base ease-out data-[popup-open]:rotate-180">
        <ChevronDownIcon aria-hidden="true" className="size-4 text-muted-foreground" />
      </NavigationMenuPrimitive.Icon>
    </NavigationMenuPrimitive.Trigger>
  )
}

/** The panel body for one entry, which slides across as you move along the row. */
function NavigationMenuContent({
  className,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Content>) {
  return (
    <NavigationMenuPrimitive.Content
      data-slot="navigation-menu-content"
      className={cn(
        "h-full w-full p-3",
        "transition-[opacity,translate] duration-base ease-out",
        "data-[starting-style]:opacity-0 data-[ending-style]:opacity-0",
        "data-[starting-style]:data-[activation-direction=left]:-translate-x-1/2",
        "data-[starting-style]:data-[activation-direction=right]:translate-x-1/2",
        "data-[ending-style]:data-[activation-direction=left]:translate-x-1/2",
        "data-[ending-style]:data-[activation-direction=right]:-translate-x-1/2",
        className
      )}
      {...props}
    />
  )
}

/**
 * The pointer between the open pill and the panel.
 *
 * Base UI calls this part Arrow and it only works inside the positioner, so
 * `NavigationMenuViewport` renders it rather than the list.
 */
function NavigationMenuIndicator({
  className,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Arrow>) {
  return (
    <NavigationMenuPrimitive.Arrow
      data-slot="navigation-menu-indicator"
      className={cn(
        "block size-2 rotate-45 bg-popover",
        "transition-[left,right] duration-base ease-out",
        "data-[side=bottom]:-top-1 data-[side=top]:-bottom-1",
        className
      )}
      {...props}
    />
  )
}

/**
 * The shared floating panel every entry opens into.
 *
 * Base UI needs a Portal, a Positioner and a Popup around its Viewport, so
 * this one export composes all four and carries the Loam paper on the Popup.
 */
function NavigationMenuViewport({
  className,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Viewport>) {
  return (
    <NavigationMenuPrimitive.Portal>
      <NavigationMenuPrimitive.Positioner
        sideOffset={8}
        collisionAvoidance={{ side: "none" }}
        className="z-50 h-(--positioner-height) w-(--positioner-width) max-w-(--available-width) outline-none transition-[top,left,right,bottom] duration-base ease-out"
      >
        <NavigationMenuPrimitive.Popup
          data-slot="navigation-menu-popup"
          className={cn(
            floatingSurfaceBase,
            "relative h-(--popup-height) w-(--popup-width) origin-(--transform-origin) outline-none",
            "transition-[opacity,scale,width,height] duration-base ease-out",
            "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
            "data-[ending-style]:scale-95 data-[ending-style]:opacity-0"
          )}
        >
          <NavigationMenuIndicator />
          <NavigationMenuPrimitive.Viewport
            data-slot="navigation-menu-viewport"
            className={cn(
              "relative h-full w-full overflow-hidden rounded-[inherit]",
              className
            )}
            {...props}
          />
        </NavigationMenuPrimitive.Popup>
      </NavigationMenuPrimitive.Positioner>
    </NavigationMenuPrimitive.Portal>
  )
}

/** A link inside a panel, on the shared warm hover. */
function NavigationMenuLink({
  className,
  ...props
}: React.ComponentProps<typeof NavigationMenuPrimitive.Link>) {
  return (
    <NavigationMenuPrimitive.Link
      data-slot="navigation-menu-link"
      className={cn(
        "flex flex-col gap-1 rounded-[var(--radius-control)] p-3 text-sm no-underline outline-none",
        "transition-colors duration-fast ease-out",
        "hover:bg-accent hover:text-accent-foreground",
        "focus-visible:ring-2 focus-visible:ring-ring/50",
        "data-[active]:bg-accent data-[active]:text-accent-foreground",
        "[&_svg:not([class*='text-'])]:text-muted-foreground [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

export {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuContent,
  NavigationMenuTrigger,
  NavigationMenuLink,
  NavigationMenuIndicator,
  NavigationMenuViewport,
  navigationMenuTriggerStyle,
}
