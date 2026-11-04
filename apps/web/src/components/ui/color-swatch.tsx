import * as React from "react"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

/*
 * Loam ColorSwatch: a full circle, so it sits on the control radius.
 *
 * The colour itself comes in as a prop, because a swatch shows the consumer's
 * palette rather than the Loam palette. Everything around it stays token based:
 * the warm hairline, the blue focus ring and the spring press.
 */

/** Props for a single colour chip. */
export interface ColorSwatchProps extends Omit<React.ComponentProps<"button">, "color"> {
  /** Any CSS colour, including a token reference such as var(--primary). */
  color?: string
  /** Name shown beside the chip. */
  label?: string
  /** Raw value shown under the label, in mono. */
  value?: string
  /** Chip size. Defaults to the medium size. */
  size?: "sm" | "default" | "lg"
  /** Marks this chip as the current choice. */
  selected?: boolean
  /** Hide the label column and show the chip alone. */
  hideLabel?: boolean
}

/** Props for a row of colour chips. */
export type ColorSwatchGroupProps = React.ComponentProps<"div">

const chipSizes = {
  sm: "size-6",
  default: "size-9",
  lg: "size-12",
} as const

/** One colour chip, clickable, with an optional name and value beside it. */
function ColorSwatch({
  className,
  color = "var(--primary)",
  label,
  value,
  size = "default",
  selected = false,
  hideLabel = false,
  ...props
}: ColorSwatchProps) {
  const chip = (
    <span
      className={cn(
        chipSizes[size],
        "relative flex shrink-0 items-center justify-center overflow-hidden",
        "rounded-[var(--radius-control)] border border-border",
        "[box-shadow:var(--shadow-2xs)]"
      )}
      style={{ backgroundColor: color }}
    >
      {selected ? <Check className="size-4 text-primary-foreground mix-blend-difference" /> : null}
    </span>
  )

  return (
    <button
      type="button"
      data-slot="color-swatch"
      aria-pressed={selected}
      aria-label={label ?? value ?? "Colour"}
      className={cn(
        "group inline-flex items-center gap-3 rounded-[var(--radius-control)] p-1 text-left cursor-pointer",
        "transition-[transform,background-color,box-shadow] duration-fast ease-out active:scale-[0.96]",
        "hover:bg-accent",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        selected && "bg-accent",
        className
      )}
      {...props}
    >
      {chip}
      {!hideLabel && (label || value) ? (
        <span className="flex min-w-0 flex-col pr-2">
          {label ? (
            <span className="truncate text-sm font-semibold text-foreground">{label}</span>
          ) : null}
          {value ? (
            <span className="truncate font-mono text-xs text-muted-foreground">{value}</span>
          ) : null}
        </span>
      ) : null}
    </button>
  )
}

/** A wrapping row of colour chips. */
function ColorSwatchGroup({ className, ...props }: ColorSwatchGroupProps) {
  return (
    <div
      data-slot="color-swatch-group"
      className={cn("flex flex-wrap items-center gap-2", className)}
      {...props}
    />
  )
}

export { ColorSwatch, ColorSwatchGroup }
