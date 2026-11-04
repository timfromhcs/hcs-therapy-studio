"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Timeline: dots on a hairline, with the entry text beside them.
 *
 * The dot is a small circle at the control tier and the connector is the same
 * warm border hairline as every card rim. A dot marked active takes the
 * primary button's flat near-black fill. The entries themselves carry no
 * surface, so a timeline can sit inside a card without a second rim.
 */

const TimelineItemContext = React.createContext<{ active: boolean }>({
  active: false,
})

/** The ordered list of timeline entries. */
function Timeline({ className, ...props }: React.ComponentProps<"ol">) {
  return (
    <ol
      data-slot="timeline"
      className={cn("flex w-full flex-col", className)}
      {...props}
    />
  )
}

/** One entry: the dot rail on the left, the text on the right. */
function TimelineItem({
  className,
  active = false,
  ...props
}: React.ComponentProps<"li"> & {
  /** Marks this entry as the one the reader is on. */
  active?: boolean
}) {
  return (
    <TimelineItemContext.Provider value={{ active }}>
      <li
        data-slot="timeline-item"
        data-active={active}
        className={cn("flex gap-4", className)}
        {...props}
      />
    </TimelineItemContext.Provider>
  )
}

/** The dot beside an entry. Active, it takes the flat primary fill. */
function TimelineIndicator({
  className,
  children,
  ...props
}: React.ComponentProps<"span">) {
  const { active } = React.useContext(TimelineItemContext)

  return (
    <span
      data-slot="timeline-indicator"
      data-active={active}
      aria-hidden="true"
      className={cn(
        "mt-1 flex size-3 shrink-0 items-center justify-center",
        "rounded-[var(--radius-control)]",
        "transition-colors duration-fast ease-out",
        active
          ? "bg-primary [box-shadow:var(--shadow-xs)]"
          : "border border-border bg-card",
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}

/** The same dot under its shorter name, for callers that prefer it. */
const TimelineDot = TimelineIndicator

/** The hairline that runs from one dot down to the next. */
function TimelineConnector({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="timeline-connector"
      aria-hidden="true"
      className={cn("w-px flex-1 bg-border", className)}
      {...props}
    />
  )
}

/** The dot rail: holds one dot and the connector beneath it. */
function TimelineSeparator({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="timeline-separator"
      className={cn("flex flex-col items-center gap-1 self-stretch", className)}
      {...props}
    />
  )
}

/** The text block for one entry. */
function TimelineContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="timeline-content"
      className={cn("flex min-w-0 flex-1 flex-col gap-1 pb-6", className)}
      {...props}
    />
  )
}

/** The entry headline. */
function TimelineTitle({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="timeline-title"
      className={cn("text-sm font-semibold text-foreground", className)}
      {...props}
    />
  )
}

/** A supporting line under an entry headline. */
function TimelineDescription({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="timeline-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

/** When the entry happened, set in the mono face so the column lines up. */
function TimelineTime({ className, ...props }: React.ComponentProps<"time">) {
  return (
    <time
      data-slot="timeline-time"
      className={cn(
        "font-mono text-xs tracking-tight text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

export {
  Timeline,
  TimelineItem,
  TimelineIndicator,
  TimelineDot,
  TimelineConnector,
  TimelineSeparator,
  TimelineContent,
  TimelineTitle,
  TimelineDescription,
  TimelineTime,
}
