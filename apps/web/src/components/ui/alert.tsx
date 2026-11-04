import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam Alert: a card-tier status panel.
 *
 * An alert is a small card, so it takes the card radius (1.5rem) and a border
 * on all four sides. Colour arrives only through a pop triad: soft surface,
 * hairline border in the same hue, ink dark enough to read on it.
 * Loam never uses a left-edge accent stripe; the whole rim carries the hue.
 */

const alertVariants = cva(
  [
    "relative grid w-full items-start gap-y-1 rounded-[var(--radius-card)] border px-5 py-4 text-sm",
    "grid-cols-[0_1fr] has-[>svg]:grid-cols-[1.25rem_1fr] gap-x-0 has-[>svg]:gap-x-3",
    "[&>svg]:size-4 [&>svg]:translate-y-0.5 [&>svg]:text-current",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "border-pop-neutral-border bg-pop-neutral-surface text-pop-neutral-ink",
        card: "border-border bg-card text-card-foreground [box-shadow:var(--shadow-sm)]",
        info: "border-pop-blue-border bg-pop-blue-surface text-pop-blue-ink",
        success:
          "border-pop-green-border bg-pop-green-surface text-pop-green-ink",
        warning:
          "border-pop-amber-border bg-pop-amber-surface text-pop-amber-ink",
        destructive:
          "border-pop-red-border bg-pop-red-surface text-pop-red-ink",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

/** The Loam status panel: card radius, a full pop-triad rim, no accent stripe. */
function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return (
    <div
      data-slot="alert"
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  )
}

/** The alert headline: semibold, one line, sitting beside the icon column. */
function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-title"
      className={cn(
        "col-start-2 min-h-4 font-semibold leading-none tracking-tight",
        className
      )}
      {...props}
    />
  )
}

/** The supporting body under an alert title, held at 90 percent of the ink. */
function AlertDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn(
        "col-start-2 grid justify-items-start gap-1 text-sm text-current/90 [&_p]:leading-relaxed",
        className
      )}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription, alertVariants }
