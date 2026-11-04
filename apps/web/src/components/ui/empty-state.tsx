"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { Button } from "./button"

/*
 * Loam EmptyState: the one-prop version of the empty card.
 *
 * Same card tier and the same centred stack as Empty, wrapped so a caller can
 * pass an icon, a title, a line of support and one action without composing
 * six sub-components.
 */

/** Props for the packaged empty state. */
export interface EmptyStateProps extends Omit<React.ComponentProps<"div">, "title"> {
  /** The glyph shown in the icon well above the title. */
  icon?: React.ReactNode
  /** The headline naming what is missing. */
  title: React.ReactNode
  /** The supporting line telling the reader what to do next. */
  description?: React.ReactNode
  /** Label for the action pill. Omit it to render no action. */
  actionLabel?: string
  /** Runs when the reader presses the action pill. */
  onAction?: () => void
  /** Render a custom action row instead of the single pill. */
  action?: React.ReactNode
}

/** A centred card-tier empty state with an icon, copy and one action pill. */
function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  action,
  className,
  children,
  ...props
}: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-6 text-center",
        "rounded-[var(--radius-card)] border border-border bg-card px-8 py-12",
        "text-card-foreground [box-shadow:var(--shadow-sm)]",
        className
      )}
      {...props}
    >
      {icon ? (
        <div
          aria-hidden="true"
          className={cn(
            "flex size-12 shrink-0 items-center justify-center",
            "rounded-[var(--radius-control)] border border-border bg-muted",
            "text-muted-foreground [&_svg:not([class*='size-'])]:size-5"
          )}
        >
          {icon}
        </div>
      ) : null}

      <div className="flex max-w-sm flex-col items-center gap-2">
        <div className="text-base font-semibold leading-none">{title}</div>
        {description ? (
          <p className="text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>

      {action ??
        (actionLabel ? (
          <Button onClick={onAction}>{actionLabel}</Button>
        ) : null)}

      {children}
    </div>
  )
}

export { EmptyState }
