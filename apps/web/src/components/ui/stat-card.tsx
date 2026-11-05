import * as React from "react"
import { Minus, TrendingDown, TrendingUp } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge } from "./badge"
import { Card, CardContent, CardHeader, CardTitle } from "./card"

/*
 * Loam StatCard: card tier, because it is a panel and not a control.
 *
 * One number carries the card. Hierarchy comes from size and weight, so the
 * label is small and quiet, the number is large and semibold, and the change
 * sits in a pop triad badge rather than in bare coloured text.
 */

/** Which way the change moved, which picks the badge triad. */
export type StatCardDirection = "up" | "down" | "flat"

/** Props for the single-metric card. */
export interface StatCardProps extends React.ComponentProps<"div"> {
  /** What the number measures, shown above it in small caps. */
  label: string
  /** The number itself, already formatted. */
  value: React.ReactNode
  /** Small glyph shown beside the label. */
  icon?: React.ReactNode
  /** The delta, for example "12.4%", shown in a pop triad badge. */
  change?: React.ReactNode
  /** Direction of the change. Defaults to flat. */
  changeDirection?: StatCardDirection
  /** One quiet line under the number, for the comparison period. */
  description?: React.ReactNode
}

const directionBadge = {
  up: { variant: "green", icon: <TrendingUp /> },
  down: { variant: "destructive", icon: <TrendingDown /> },
  flat: {
    variant: "outline",
    className: "border-pop-neutral-border bg-pop-neutral-surface text-pop-neutral-ink",
    icon: <Minus />,
  },
} satisfies Record<
  StatCardDirection,
  {
    variant: "green" | "outline" | "destructive"
    className?: string
    icon: React.ReactNode
  }
>

/** A card showing one metric, its change and one line of context. */
function StatCard({
  className,
  label,
  value,
  icon,
  change,
  changeDirection = "flat",
  description,
  ...props
}: StatCardProps) {
  const delta = directionBadge[changeDirection]

  return (
    <Card data-slot="stat-card" className={cn("gap-3", className)} {...props}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          {icon ? (
            <span className="[&_svg]:size-4 [&_svg]:shrink-0" aria-hidden="true">
              {icon}
            </span>
          ) : null}
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          {/*
            `break-words` plus a modest base size: an identifier like
            "VULKAN_BALANCED" has no space to wrap at, so at text-4xl it was
            silently clipped by the card instead of overflowing the page — which
            is exactly the failure an overflow assertion cannot see.
          */}
          <span className="min-w-0 break-words text-3xl font-semibold tracking-tight tabular-nums text-foreground">
            {value}
          </span>
          {change ? (
            <Badge
              variant={delta.variant}
              className={"className" in delta ? delta.className : undefined}
            >
              {delta.icon}
              {change}
            </Badge>
          ) : null}
        </div>
        {description ? (
          <p className="text-sm text-muted-foreground">{description}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}

export { StatCard }
