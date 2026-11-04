import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam TabsSubtle: the quiet version of the pill rail.
 *
 * Same control-tier pill shape and same muted rail as Tabs. The only change is
 * the selected trigger: a white card fill held by a warm hairline instead of
 * the near-black primary fill. Use it when the tabs sit beside a page title
 * and the near-black would outweigh it. Still no shadow on the inner pill.
 */

/** The quiet tabs root: holds the selected value for a rail and its panels. */
function TabsSubtle({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs-subtle"
      className={cn("flex flex-col gap-4", className)}
      {...props}
    />
  )
}

/** The muted pill rail. Identical shape to Tabs, so the two can sit together. */
function TabsSubtleList({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-subtle-list"
      className={cn(
        "inline-flex w-fit items-center justify-center gap-1",
        "rounded-[var(--radius-control)] bg-muted p-1 text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/** One quiet tab. Selected, it is a white pill with a hairline, no fill jump. */
function TabsSubtleTrigger({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-subtle-trigger"
      className={cn(
        "inline-flex h-8 flex-1 items-center justify-center gap-1.5 whitespace-nowrap",
        "rounded-[var(--radius-control)] border border-transparent px-4 text-sm font-semibold",
        "cursor-pointer select-none",
        "transition-[transform,background-color,color,border-color] duration-fast ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        pressSpring,
        "hover:text-foreground",
        "data-[state=active]:border-border data-[state=active]:bg-card data-[state=active]:text-foreground",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

/** The panel for one quiet tab. */
function TabsSubtleContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-subtle-content"
      className={cn("flex-1 text-sm outline-none", className)}
      {...props}
    />
  )
}

/** Alias so a showcase can import the quiet set under the plain tab names. */
const Tabs = TabsSubtle
/** Alias for the quiet rail, matching the plain tab naming. */
const TabsList = TabsSubtleList
/** Alias for the quiet trigger, matching the plain tab naming. */
const TabsTrigger = TabsSubtleTrigger
/** Alias for the quiet panel, matching the plain tab naming. */
const TabsContent = TabsSubtleContent

export {
  TabsSubtle,
  TabsSubtleList,
  TabsSubtleTrigger,
  TabsSubtleContent,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
}
