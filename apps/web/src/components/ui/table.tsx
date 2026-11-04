"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Table: the card tier holds the whole table, the rows hold nothing.
 *
 * The outer wrapper is the white squircle with the warm hairline and the soft
 * card float. Rows are separated by the border token alone, because a shadow
 * on a row reads as a rendering bug rather than depth.
 */

/** The table surface: a white card squircle that scrolls sideways inside itself. */
function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div
      data-slot="table-container"
      className="relative w-full overflow-hidden rounded-[var(--radius-card)] border border-border bg-card [box-shadow:var(--shadow-sm)]"
    >
      <div className="w-full overflow-x-auto">
        <table
          data-slot="table"
          className={cn("w-full caption-bottom text-sm text-card-foreground", className)}
          {...props}
        />
      </div>
    </div>
  )
}

/** Header band: quiet uppercase labels over one hairline. */
function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b [&_tr]:border-border", className)}
      {...props}
    />
  )
}

/** Row group for the data rows. The last row drops its hairline. */
function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <tbody
      data-slot="table-body"
      className={cn("[&_tr:last-child]:border-0", className)}
      {...props}
    />
  )
}

/** Summary band at the foot of the table, held by a hairline and a warm tint. */
function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        "border-t border-border bg-muted/50 font-semibold [&>tr:last-child]:border-0",
        className
      )}
      {...props}
    />
  )
}

/** One row. Hover deepens the surface, and the hairline is the only separator. */
function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        "border-b border-border transition-colors duration-fast",
        "hover:bg-accent/60 data-[state=selected]:bg-accent",
        className
      )}
      {...props}
    />
  )
}

/** Column label: small, semibold and quiet, so the data carries the weight. */
function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "h-11 px-4 text-left align-middle text-xs font-semibold tracking-wide whitespace-nowrap text-muted-foreground uppercase",
        "[&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

/** One data cell. */
function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        "px-4 py-3 align-middle whitespace-nowrap",
        "[&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

/** The line under the table that says what the table is. */
function TableCaption({ className, ...props }: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("px-4 pt-3 pb-4 text-left text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}
