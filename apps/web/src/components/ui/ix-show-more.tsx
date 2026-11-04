import * as React from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam ShowMore: a clamped block of prose with a control-tier toggle.
 *
 * The block clamps to a line count and a height ceiling, with no fade overlay,
 * because Loam fills stay flat. The toggle is a pill, because it is a control,
 * and it shares the system press spring.
 */

/** Props for the clamped prose block. */
export interface ShowMoreProps extends React.ComponentProps<"div"> {
  /** Lines to show while collapsed. Defaults to 3. */
  lines?: number
  /** Collapsed height ceiling in pixels, used for the height transition. */
  maxHeight?: number
  /** What the content is, used in the toggle label. */
  label?: string
}

/** A clamped block of prose with a pill toggle that reveals the rest. */
function ShowMore({
  lines = 3,
  maxHeight = 168,
  label,
  className,
  children,
  ...props
}: ShowMoreProps) {
  const [expanded, setExpanded] = React.useState(false)

  return (
    <div
      data-slot="show-more"
      className={cn("flex w-full flex-col gap-3", className)}
      {...props}
    >
      <div
        className="overflow-hidden text-sm leading-relaxed text-muted-foreground"
        style={
          expanded
            ? undefined
            : {
                display: "-webkit-box",
                WebkitBoxOrient: "vertical",
                WebkitLineClamp: lines,
                maxHeight: `${maxHeight}px`,
              }
        }
      >
        {children}
      </div>

      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((open) => !open)}
        className={cn(
          "inline-flex w-fit cursor-pointer select-none items-center gap-1.5",
          "rounded-[var(--radius-control)] border border-border bg-card px-3.5 py-1.5",
          "text-xs font-semibold text-foreground [box-shadow:var(--shadow-2xs)]",
          "transition-[transform,background-color,border-color,color] duration-fast ease-out",
          "hover:bg-accent hover:border-foreground/20 hover:text-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          pressSpring
        )}
      >
        {expanded ? "Show less" : "Show more"}
        {label ? (
          <span className="font-normal text-muted-foreground">{label}</span>
        ) : null}
        <ChevronDown
          className={cn(
            "size-3.5 transition-transform duration-base ease-out",
            expanded && "rotate-180"
          )}
        />
      </button>
    </div>
  )
}

export { ShowMore }
