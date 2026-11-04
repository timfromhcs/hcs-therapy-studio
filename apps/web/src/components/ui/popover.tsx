"use client"

import * as React from "react"
import { Popover as PopoverPrimitive } from "@base-ui/react/popover"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase } from "./_shared"

/*
 * Loam Popover: the first of the floating surfaces.
 *
 * Every floating surface in Loam shares one recipe, floatingSurfaceBase, so a
 * popover, a menu and a tooltip read as the same sheet of paper at the card
 * radius (1.5rem) with the soft large float.
 */

/** Root of the popover. */
function Popover({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Root>) {
  return <PopoverPrimitive.Root {...props} />
}

/** The control that opens the popover. */
function PopoverTrigger({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Trigger>) {
  return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />
}

/**
 * The floating popover surface.
 *
 * Base UI splits Radix's single Content into a Positioner that places the
 * surface and a Popup that is the surface, so the placement props land on the
 * Positioner and the Loam paper lands on the Popup.
 */
function PopoverContent({
  className,
  align = "center",
  sideOffset = 8,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Popup> & {
  /** Where the surface lines up against its trigger. */
  align?: "start" | "center" | "end"
  /** Gap in pixels between the trigger and the surface. */
  sideOffset?: number
}) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Positioner
        align={align}
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <PopoverPrimitive.Popup
          data-slot="popover-content"
          className={cn(
            floatingSurfaceBase,
            "w-72 origin-(--transform-origin) p-5 outline-none",
            "transition-[opacity,scale] duration-base ease-out",
            "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
            "data-[ending-style]:scale-95 data-[ending-style]:opacity-0",
            className
          )}
          {...props}
        />
      </PopoverPrimitive.Positioner>
    </PopoverPrimitive.Portal>
  )
}

/**
 * Anchors the popover to an element other than its trigger.
 *
 * Base UI has no Anchor part: its Positioner takes an `anchor` element or ref
 * instead. This keeps the Radix-shaped export as a plain wrapper you can ref,
 * then pass that ref to the Positioner when you need a custom anchor.
 */
function PopoverAnchor({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="popover-anchor"
      className={cn("contents", className)}
      {...props}
    />
  )
}

export { Popover, PopoverTrigger, PopoverContent, PopoverAnchor }
