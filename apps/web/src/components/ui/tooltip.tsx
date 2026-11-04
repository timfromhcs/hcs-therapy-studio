"use client"

import * as React from "react"
import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase } from "./_shared"

/*
 * Loam Tooltip: the smallest floating surface, same recipe as the others.
 *
 * It is white paper with a warm hairline, not an inverted chip, so every
 * floating thing in Loam is one material. At tooltip height the card radius
 * reads as a pill, which is exactly the intent.
 */

/**
 * Wraps a tree so its tooltips share one open and close timer.
 *
 * Base UI names the wait `delay` where Radix names it `delayDuration`, so this
 * keeps the Radix name and maps it.
 */
function TooltipProvider({
  delayDuration = 0,
  ...props
}: Omit<React.ComponentProps<typeof TooltipPrimitive.Provider>, "delay"> & {
  /** Milliseconds to wait before a tooltip opens. */
  delayDuration?: number
}) {
  return <TooltipPrimitive.Provider delay={delayDuration} {...props} />
}

/** Root of a single tooltip, with its own provider for standalone use. */
function Tooltip({
  ...props
}: React.ComponentProps<typeof TooltipPrimitive.Root>) {
  return (
    <TooltipProvider>
      <TooltipPrimitive.Root {...props} />
    </TooltipProvider>
  )
}

/** The element the tooltip describes. */
function TooltipTrigger({
  ...props
}: React.ComponentProps<typeof TooltipPrimitive.Trigger>) {
  return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />
}

/* Arrow controls, kept so callers can hide or restyle the pointer. */
interface TooltipContentProps
  extends React.ComponentProps<typeof TooltipPrimitive.Popup> {
  /** Extra classes for the pointer. */
  arrowClassName?: string
  /** Colour for the pointer's rim. */
  arrowStroke?: string
  /** Width in pixels of the pointer's rim. */
  arrowStrokeWidth?: number
  /** Drop the pointer and keep only the surface. */
  hideArrow?: boolean
  /** Gap in pixels between the trigger and the surface. */
  sideOffset?: number
}

/**
 * The floating tooltip surface and its pointer.
 *
 * Base UI splits Radix's Content into a Positioner and a Popup, and its Arrow
 * is a styled element rather than an SVG, so the pointer is a rotated square
 * in the popover colour and the stroke props set its rim.
 */
function TooltipContent({
  className,
  arrowClassName,
  arrowStroke,
  arrowStrokeWidth = 2,
  hideArrow = false,
  sideOffset = 6,
  children,
  ...props
}: TooltipContentProps) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Positioner
        sideOffset={sideOffset}
        className="z-50 outline-none"
      >
        <TooltipPrimitive.Popup
          data-slot="tooltip-content"
          className={cn(
            floatingSurfaceBase,
            "w-fit origin-(--transform-origin) px-3 py-1.5 text-xs font-semibold text-balance outline-none",
            "transition-[opacity,scale] duration-fast ease-out",
            "data-[starting-style]:scale-95 data-[starting-style]:opacity-0",
            "data-[ending-style]:scale-95 data-[ending-style]:opacity-0",
            className
          )}
          {...props}
        >
          {children}
          {!hideArrow && (
            <TooltipPrimitive.Arrow
              className={cn(
                "block size-2 rotate-45 bg-popover",
                "data-[side=bottom]:-top-1 data-[side=top]:-bottom-1",
                "data-[side=left]:-right-1 data-[side=right]:-left-1",
                arrowClassName
              )}
              style={
                arrowStroke
                  ? {
                      borderColor: arrowStroke,
                      borderWidth: arrowStrokeWidth,
                      borderStyle: "solid",
                    }
                  : undefined
              }
            />
          )}
        </TooltipPrimitive.Popup>
      </TooltipPrimitive.Positioner>
    </TooltipPrimitive.Portal>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
