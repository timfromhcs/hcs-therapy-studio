import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam Badge: a small pill chip.
 *
 * The accent variants draw on the pop triads: a soft warm-page-friendly
 * surface, a hairline border in the same hue, and ink dark enough to read on
 * it. That triad is what keeps a status chip legible without shouting, and it
 * is the only place colour is allowed to carry meaning.
 */

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 " +
    "rounded-[var(--radius-control)] border px-2.5 py-0.5 " +
    "text-xs font-semibold whitespace-nowrap " +
    "transition-colors duration-fast " +
    "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-3",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-border bg-secondary text-secondary-foreground",
        outline: "border-border bg-transparent text-foreground",
        muted: "border-transparent bg-[color:oklch(0.885_0.009_86)] text-[color:oklch(0.48_0.009_80)]",
        blue: "border-pop-blue-border bg-pop-blue-surface text-pop-blue-ink dark:text-[color:oklch(0.875_0.064_248)]",
        green: "border-pop-green-border bg-pop-green-surface text-pop-green-ink dark:text-[color:oklch(0.875_0.13_150)]",
        orange: "border-pop-orange-border bg-pop-orange-surface text-pop-orange-ink dark:text-[color:oklch(0.875_0.069_38)]",
        purple: "border-pop-purple-border bg-pop-purple-surface text-pop-purple-ink dark:text-[color:oklch(0.875_0.065_288)]",
        pink: "border-pop-pink-border bg-pop-pink-surface text-pop-pink-ink dark:text-[color:oklch(0.875_0.084_345)]",
        amber: "border-pop-amber-border bg-pop-amber-surface text-pop-amber-ink dark:text-[color:oklch(0.875_0.12_88)]",
        success: "border-pop-green-border bg-pop-green-surface text-pop-green-ink dark:text-[color:oklch(0.875_0.13_150)]",
        warning: "border-pop-amber-border bg-pop-amber-surface text-pop-amber-ink dark:text-[color:oklch(0.875_0.12_88)]",
        info: "border-pop-blue-border bg-pop-blue-surface text-pop-blue-ink dark:text-[color:oklch(0.875_0.064_248)]",
        destructive: "border-pop-red-border bg-pop-red-surface text-pop-red-ink dark:text-[color:oklch(0.875_0.067_32)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

/** Props for the Loam chip, including its cva variant. */
export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

/** A small pill chip for status, category and counts. */
const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="badge"
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
)
Badge.displayName = "Badge"

export { Badge, badgeVariants }
