import * as React from "react"
import { PreviewCard as PreviewCardPrimitive } from "@base-ui/react/preview-card"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase } from "./_shared"

/*
 * Loam HoverCard: a floating surface, same recipe as Popover.
 *
 * It carries the card radius (1.5rem) and the soft large float, so a preview
 * that appears on hover is the same paper as a menu or a popover.
 */

/**
 * Root of the hover preview.
 *
 * Base UI calls this component PreviewCard, so this file keeps the Radix
 * HoverCard export names over that primitive.
 */
function HoverCard({
  ...props
}: React.ComponentProps<typeof PreviewCardPrimitive.Root>) {
  return <PreviewCardPrimitive.Root {...props} />
}

/** The element that reveals the preview on hover or focus. */
function HoverCardTrigger({
  ...props
}: React.ComponentProps<typeof PreviewCardPrimitive.Trigger>) {
  return (
    <PreviewCardPrimitive.Trigger data-slot="hover-card-trigger" {...props} />
  )
}

/**
 * The floating preview surface.
 *
 * Base UI splits Radix's Content into a Positioner that places the surface and
 * a Popup that is the surface.
 */
function HoverCardContent({
  className,
  align = "center",
  sideOffset = 8,
  ...props
}: React.ComponentProps<typeof PreviewCardPrimitive.Popup> & {
  /** Where the surface lines up against its trigger. */
  align?: "start" | "center" | "end"
  /** Gap in pixels between the trigger and the surface. */
  sideOffset?: number
}) {
  return (
    <PreviewCardPrimitive.Portal>
      <PreviewCardPrimitive.Positioner
        align={align}
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <PreviewCardPrimitive.Popup
          data-slot="hover-card-content"
          className={cn(
            floatingSurfaceBase,
            "w-64 origin-(--transform-origin) p-5 outline-none",
            "transition-[opacity,scale] duration-fast ease-out",
            "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
            "data-[ending-style]:scale-95 data-[ending-style]:opacity-0",
            className
          )}
          {...props}
        />
      </PreviewCardPrimitive.Positioner>
    </PreviewCardPrimitive.Portal>
  )
}

export { HoverCard, HoverCardTrigger, HoverCardContent }
