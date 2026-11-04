"use client"

import * as React from "react"
import { Collapsible as CollapsiblePrimitive } from "@base-ui/react/collapsible"

import { cn } from "@/lib/utils"

/*
 * Loam Collapsible: the open and shut mechanic with no surface of its own.
 *
 * The root carries no radius, because whatever wraps it owns the shape. Only
 * the content adds motion, so a disclosure grows the page instead of snapping
 * it. Use Accordion when the section needs the card squircle.
 */

/** The disclosure root: holds the open state for a trigger and its content. */
function Collapsible({
  className,
  ...props
}: React.ComponentProps<typeof CollapsiblePrimitive.Root>) {
  return (
    <CollapsiblePrimitive.Root
      data-slot="collapsible"
      className={cn("w-full", className)}
      {...props}
    />
  )
}

/** The control that opens and shuts the section. */
function CollapsibleTrigger({
  ...props
}: React.ComponentProps<typeof CollapsiblePrimitive.Trigger>) {
  return (
    <CollapsiblePrimitive.Trigger
      data-slot="collapsible-trigger"
      {...props}
    />
  )
}

/**
 * The revealed section, which slides open on the Loam easing.
 *
 * Base UI calls this part Panel and publishes its measured height as
 * `--collapsible-panel-height`, so the slide is a height transition rather
 * than the Radix keyframe pair.
 */
function CollapsibleContent({
  className,
  ...props
}: React.ComponentProps<typeof CollapsiblePrimitive.Panel>) {
  return (
    <CollapsiblePrimitive.Panel
      data-slot="collapsible-content"
      className={cn(
        "h-[var(--collapsible-panel-height)] overflow-hidden text-sm",
        "transition-[height] duration-base ease-out",
        "data-[starting-style]:h-0 data-[ending-style]:h-0",
        className
      )}
      {...props}
    />
  )
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
