import { cn } from "@/lib/utils"

/*
 * Loam Skeleton: the quietest surface in the system.
 *
 * It borrows the radius of whatever it stands in for, so the caller passes
 * that radius in. The default is the card squircle, because most placeholders
 * sit inside a card. Colour is the muted warm neutral, never a cold grey.
 */

/** A muted warm placeholder block that pulses while real content loads. */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-[var(--radius-card)] bg-muted",
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
