import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam Item: a list row on the card tier.
 *
 * A row is card-sized, so it takes the card radius (1.5rem). It carries no
 * shadow, because a stack of floating rows reads as clutter. Hover deepens the
 * surface to the warm accent instead of tinting it.
 */

const itemVariants = cva(
  [
    "group/item flex flex-wrap items-center gap-4 rounded-[var(--radius-card)] text-sm",
    "transition-colors duration-fast ease-out",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "[a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "bg-transparent hover:bg-accent hover:text-accent-foreground",
        outline:
          "border border-border bg-card hover:bg-accent hover:text-accent-foreground",
        muted: "bg-muted hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "px-4 py-3",
        sm: "px-3 py-2 gap-3",
        lg: "px-5 py-4",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

/** Props for a list row, including its surface variant and density. */
export interface ItemProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof itemVariants> {
  /** Render the row styling onto the single child element, such as a link. */
  asChild?: boolean
}

/** A list row: card radius, warm hover, no shadow. */
function Item({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ItemProps) {
  const Comp = asChild ? Slot : "div"
  return (
    <Comp
      data-slot="item"
      className={cn(itemVariants({ variant, size, className }))}
      {...props}
    />
  )
}

/** Stacks rows with a small gap so each one keeps its own squircle. */
function ItemGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-group"
      role="list"
      className={cn("flex w-full flex-col gap-1", className)}
      {...props}
    />
  )
}

/** A warm hairline between rows, inset so it does not touch the radius. */
function ItemSeparator({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-separator"
      role="separator"
      className={cn("mx-4 h-px shrink-0 bg-border", className)}
      {...props}
    />
  )
}

/** Props for the leading slot of a row, including its media shape. */
export interface ItemMediaProps extends React.ComponentProps<"div"> {
  /** `icon` draws a pill tile around the glyph, `image` keeps a bare frame. */
  variant?: "default" | "icon" | "image"
}

/** The leading slot of a row: an icon tile, an avatar or a thumbnail. */
function ItemMedia({
  className,
  variant = "default",
  ...props
}: ItemMediaProps) {
  return (
    <div
      data-slot="item-media"
      data-variant={variant}
      className={cn(
        "flex shrink-0 items-center justify-center gap-2 text-muted-foreground",
        variant === "icon" &&
          "size-9 rounded-[var(--radius-control)] border border-border bg-muted [&_svg:not([class*='size-'])]:size-4",
        variant === "image" &&
          "size-10 overflow-hidden rounded-[var(--radius-card)] border border-border [&_img]:size-full [&_img]:object-cover",
        variant === "default" && "[&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

/** The text column of a row, holding the title and description. */
function ItemContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-content"
      className={cn(
        "flex min-w-0 flex-1 flex-col gap-0.5 [&+[data-slot=item-actions]]:shrink-0",
        className
      )}
      {...props}
    />
  )
}

/** The row headline. */
function ItemTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-title"
      className={cn(
        "flex w-fit items-center gap-2 text-sm font-semibold leading-snug",
        className
      )}
      {...props}
    />
  )
}

/** The supporting line under a row title. */
function ItemDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <p
      data-slot="item-description"
      className={cn(
        "line-clamp-2 text-sm leading-relaxed text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/** The trailing slot of a row, usually a pill button or a chip. */
function ItemActions({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-actions"
      className={cn("flex shrink-0 items-center gap-2", className)}
      {...props}
    />
  )
}

/** An optional header strip above a row's content. */
function ItemHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-header"
      className={cn(
        "flex basis-full items-center justify-between gap-2",
        className
      )}
      {...props}
    />
  )
}

/** An optional footer strip below a row's content. */
function ItemFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="item-footer"
      className={cn(
        "flex basis-full items-center justify-between gap-2 text-xs text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

export {
  Item,
  ItemGroup,
  ItemSeparator,
  ItemMedia,
  ItemContent,
  ItemTitle,
  ItemDescription,
  ItemActions,
  ItemHeader,
  ItemFooter,
  itemVariants,
}
