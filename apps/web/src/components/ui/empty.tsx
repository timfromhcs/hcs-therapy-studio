import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam Empty: a centred card-tier placeholder state.
 *
 * It is a card, so it takes the card radius (1.5rem) and a hairline on all
 * four sides. The media well inside it is a smaller square, so it steps down
 * to the control pill and stays a circle at that size.
 */

const emptyMediaVariants = cva(
  "flex shrink-0 items-center justify-center [&_svg]:pointer-events-none",
  {
    variants: {
      variant: {
        default: "text-muted-foreground [&_svg:not([class*='size-'])]:size-6",
        icon: [
          "size-12 rounded-[var(--radius-control)] border border-border bg-muted",
          "text-muted-foreground [&_svg:not([class*='size-'])]:size-5",
        ].join(" "),
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

/** The centred placeholder card shown when a list or view has no content. */
function Empty({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-6 text-center",
        "rounded-[var(--radius-card)] border border-border bg-card px-8 py-12",
        "text-card-foreground [box-shadow:var(--shadow-sm)]",
        className
      )}
      {...props}
    />
  )
}

/** Groups the media, title and description so they stack as one unit. */
function EmptyHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty-header"
      className={cn(
        "flex max-w-sm flex-col items-center gap-3 text-center",
        className
      )}
      {...props}
    />
  )
}

/** Props for the media well, including its icon-tile variant. */
export interface EmptyMediaProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof emptyMediaVariants> {}

/** The icon or illustration well above the title. */
function EmptyMedia({ className, variant, ...props }: EmptyMediaProps) {
  return (
    <div
      data-slot="empty-media"
      aria-hidden="true"
      className={cn(emptyMediaVariants({ variant }), className)}
      {...props}
    />
  )
}

/** The headline that names what is missing. */
function EmptyTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty-title"
      className={cn("text-base font-semibold leading-none", className)}
      {...props}
    />
  )
}

/** The supporting line that says what the reader can do next. */
function EmptyDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty-description"
      className={cn(
        "text-sm leading-relaxed text-muted-foreground [&_a]:underline [&_a]:underline-offset-4",
        className
      )}
      {...props}
    />
  )
}

/** The action row under the copy, usually holding one Loam Button. */
function EmptyContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="empty-content"
      className={cn(
        "flex w-full flex-col items-center justify-center gap-3 text-sm sm:flex-row",
        className
      )}
      {...props}
    />
  )
}

export {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
  EmptyContent,
  emptyMediaVariants,
}
