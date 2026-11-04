import * as React from "react"
import * as ResizablePrimitive from "react-resizable-panels"
import { GripVerticalIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/*
 * Loam Resizable: one card, split by a hairline.
 *
 * The group is the card-tier surface (rounded-[var(--radius-card)], warm
 * hairline, soft card float) and it clips its children, so the panels inherit
 * that squircle at the corners instead of each drawing a rim of their own.
 * The handle is the same border hairline, with a control-tier grip on it.
 */

/** The card surface that holds the panels and clips them to its squircle. */
function ResizablePanelGroup({
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelGroup>) {
  return (
    <ResizablePrimitive.PanelGroup
      data-slot="resizable-panel-group"
      className={cn(
        "flex h-full w-full overflow-hidden",
        "rounded-[var(--radius-card)] border border-border bg-card",
        "[box-shadow:var(--shadow-sm)]",
        "data-[panel-group-direction=vertical]:flex-col",
        className
      )}
      {...props}
    />
  )
}

/** One region inside the group. It takes its shape from the group. */
function ResizablePanel({
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.Panel>) {
  return (
    <ResizablePrimitive.Panel
      data-slot="resizable-panel"
      className={cn("bg-card text-card-foreground", className)}
      {...props}
    />
  )
}

/** The draggable divider, with an optional grip pill at its centre. */
function ResizableHandle({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof ResizablePrimitive.PanelResizeHandle> & {
  /** Show a grip pill on the divider so the drag target is obvious. */
  withHandle?: boolean
}) {
  return (
    <ResizablePrimitive.PanelResizeHandle
      data-slot="resizable-handle"
      className={cn(
        "relative flex w-px items-center justify-center bg-border",
        "transition-colors duration-fast ease-out hover:bg-foreground/20",
        "after:absolute after:inset-y-0 after:left-1/2 after:w-2 after:-translate-x-1/2",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        "data-[panel-group-direction=vertical]:h-px data-[panel-group-direction=vertical]:w-full",
        "data-[panel-group-direction=vertical]:after:left-0 data-[panel-group-direction=vertical]:after:h-2",
        "data-[panel-group-direction=vertical]:after:w-full data-[panel-group-direction=vertical]:after:translate-x-0",
        "data-[panel-group-direction=vertical]:after:-translate-y-1/2",
        "[&[data-panel-group-direction=vertical]>div]:rotate-90",
        className
      )}
      {...props}
    >
      {withHandle && (
        <div className="z-10 flex h-5 w-3.5 items-center justify-center rounded-[var(--radius-control)] border border-border bg-card text-muted-foreground">
          <GripVerticalIcon className="size-2.5" />
        </div>
      )}
    </ResizablePrimitive.PanelResizeHandle>
  )
}

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }
