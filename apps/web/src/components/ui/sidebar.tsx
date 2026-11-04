"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Sidebar: a card-tier panel holding control-tier rows.
 *
 * The panel is the card squircle (1.5rem) with a warm hairline and the soft
 * card float, because it is a surface. Every nav row inside it is a full pill
 * at the control tier, and an active row takes the primary button's flat
 * near-black fill. No row carries a rim or a shadow of its own.
 */

/** The navigation panel: a white card squircle that holds the nav rows. */
function Sidebar({ className, ...props }: React.ComponentProps<"nav">) {
  return (
    <nav
      data-slot="sidebar"
      className={cn(
        "flex w-64 shrink-0 flex-col gap-4 overflow-hidden p-3",
        "rounded-[var(--radius-card)] border border-border bg-sidebar text-sidebar-foreground",
        "[box-shadow:var(--shadow-sm)]",
        className
      )}
      {...props}
    />
  )
}

/** The top of the panel, usually the product mark or the workspace name. */
function SidebarHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-header"
      className={cn(
        "flex shrink-0 items-center gap-2 px-3 pt-1 text-sm font-semibold",
        className
      )}
      {...props}
    />
  )
}

/** The scrolling middle of the panel, where the groups and rows live. */
function SidebarContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-content"
      className={cn("flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto", className)}
      {...props}
    />
  )
}

/** The bottom of the panel, usually the account row or a support link. */
function SidebarFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-footer"
      className={cn(
        "mt-auto flex shrink-0 flex-col gap-1 border-t border-border pt-3",
        className
      )}
      {...props}
    />
  )
}

/** A titled set of related nav rows. */
function SidebarGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group"
      className={cn("flex w-full min-w-0 flex-col gap-1", className)}
      {...props}
    />
  )
}

/** The quiet heading above a group. It names the set, never shouts. */
function SidebarGroupLabel({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group-label"
      className={cn(
        "flex h-7 shrink-0 items-center px-3 text-xs font-semibold tracking-wide text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/* Props for one nav row. Kept internal, because the showcase spreads this
   module's exports and the contract is exactly the seven components below. */
interface SidebarItemProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** A leading glyph, sized to the row by the row itself. */
  icon?: React.ReactNode
  /** Marks this row as the page the reader is on. */
  active?: boolean
}

/** One nav row: a control-tier pill that fills with near-black when active. */
const SidebarItem = React.forwardRef<HTMLButtonElement, SidebarItemProps>(
  ({ className, icon, active = false, children, ...props }, ref) => (
    <button
      ref={ref}
      type="button"
      data-slot="sidebar-item"
      data-active={active}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex w-full items-center gap-2.5 overflow-hidden whitespace-nowrap",
        "h-10 rounded-[var(--radius-control)] px-3 text-left text-sm font-semibold",
        "cursor-pointer select-none text-muted-foreground",
        "transition-[transform,background-color,color,box-shadow] duration-fast ease-out",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        pressSpring,
        active &&
          "bg-primary text-primary-foreground [box-shadow:var(--shadow-xs)] hover:bg-primary/90 hover:text-primary-foreground",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    >
      {icon}
      <span className="min-w-0 flex-1 truncate">{children}</span>
    </button>
  )
)
SidebarItem.displayName = "SidebarItem"

export {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarItem,
}
