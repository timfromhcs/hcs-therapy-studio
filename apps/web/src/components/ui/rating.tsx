"use client"

import * as React from "react"
import { Star } from "lucide-react"

import { cn } from "@/lib/utils"

/*
 * Loam Rating: a row of stars, each one a control-radius hit target.
 *
 * A filled star uses the amber pop ink, which is the only place colour carries
 * meaning here. An empty star drops to the border tone, so the row reads as a
 * score rather than as decoration.
 */

/** Props for the star rating. Leave out onChange for a read-only score. */
export interface RatingProps extends Omit<React.ComponentProps<"div">, "onChange"> {
  /** Stars filled, counted from the left. */
  value?: number
  /** Total stars offered. Defaults to five. */
  max?: number
  /** Called with the new score when a star is clicked. */
  onChange?: (value: number) => void
  /** Star size. Defaults to the medium size. */
  size?: "sm" | "default" | "lg"
  /** Show the score beside the stars. */
  showValue?: boolean
  disabled?: boolean
  /** Accessible group name. Defaults to "Rating". */
  label?: string
}

const sizeClasses = {
  sm: "size-3.5",
  default: "size-5",
  lg: "size-7",
} as const

/** A star score, read-only by default and clickable when onChange is given. */
function Rating({
  className,
  value = 0,
  max = 5,
  onChange,
  size = "default",
  showValue = false,
  disabled = false,
  label = "Rating",
  ...props
}: RatingProps) {
  const interactive = Boolean(onChange) && !disabled
  const stars = Array.from({ length: max }, (_, index) => index + 1)

  return (
    <div
      data-slot="rating"
      role={interactive ? "radiogroup" : "img"}
      aria-label={interactive ? label : `${label}: ${value} out of ${max}`}
      className={cn("inline-flex items-center gap-1.5", className)}
      {...props}
    >
      <span className="inline-flex items-center gap-0.5">
        {stars.map((star) => {
          const filled = star <= Math.round(value)
          const icon = (
            <Star
              className={cn(
                sizeClasses[size],
                "transition-colors duration-fast",
                filled ? "fill-pop-amber-ink text-pop-amber-ink" : "fill-transparent text-border"
              )}
            />
          )

          if (!interactive) {
            return (
              <span key={star} aria-hidden="true" className="inline-flex">
                {icon}
              </span>
            )
          }

          return (
            <button
              key={star}
              type="button"
              role="radio"
              aria-checked={star === Math.round(value)}
              aria-label={`${star} of ${max}`}
              onClick={() => onChange?.(star)}
              className={cn(
                "inline-flex rounded-[var(--radius-control)] p-0.5 cursor-pointer",
                "transition-transform duration-fast ease-out active:scale-[0.96]",
                "hover:text-pop-amber-ink",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              )}
            >
              {icon}
            </button>
          )
        })}
      </span>
      {showValue ? (
        <span className="text-sm font-semibold tabular-nums text-muted-foreground">
          {value.toFixed(1)}
        </span>
      ) : null}
    </div>
  )
}

export { Rating }
