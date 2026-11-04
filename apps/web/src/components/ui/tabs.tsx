"use client"

import * as React from "react"
import { Tabs as TabsPrimitive } from "@base-ui/react/tabs"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Tabs: a pill nested inside a pill rail.
 *
 * The list is a muted rail at the control tier with inner padding, and the
 * active trigger is a pill that nests inside it. The rail carries no shadow
 * and the trigger carries no rim, so a tab never reads as a floating lozenge.
 * The active fill is the flat near-black of the primary button, nothing more.
 */

/** The tabs root: holds the selected value for a rail and its panels. */
function Tabs({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      className={cn("flex flex-col gap-4", className)}
      {...props}
    />
  )
}

/** The pill rail that holds the triggers. It has padding, never a shadow. */
function TabsList({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn(
        "inline-flex w-fit items-center justify-center gap-1",
        "rounded-[var(--radius-control)] bg-muted p-1 text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/**
 * One tab. Selected, it takes the primary button's flat near-black fill.
 *
 * Base UI calls this part Tab and marks the selected one with `data-active`
 * where Radix writes `data-state="active"`.
 */
function TabsTrigger({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Tab>) {
  return (
    <TabsPrimitive.Tab
      data-slot="tabs-trigger"
      className={cn(
        "inline-flex h-8 flex-1 items-center justify-center gap-1.5 whitespace-nowrap",
        "rounded-[var(--radius-control)] px-4 text-sm font-semibold",
        "cursor-pointer select-none",
        "transition-[transform,background-color,color,box-shadow] duration-fast ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        pressSpring,
        "hover:text-foreground",
        "data-[active]:bg-primary data-[active]:text-primary-foreground data-[active]:[box-shadow:var(--shadow-xs)]",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

/**
 * The panel for one tab.
 *
 * Base UI calls this part Panel, so this export keeps the Radix name.
 */
function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Panel>) {
  return (
    <TabsPrimitive.Panel
      data-slot="tabs-content"
      className={cn("flex-1 text-sm outline-none", className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
