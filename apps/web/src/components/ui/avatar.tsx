"use client"

import * as React from "react"
import { Avatar as AvatarPrimitive } from "@base-ui/react/avatar"

import { cn } from "@/lib/utils"

/*
 * Loam Avatar: a full circle, so it takes the control radius.
 *
 * A face is never a squircle. The circle is held by the same warm hairline as
 * every other Loam surface, and the fallback sits on the muted paper tone.
 */

/** The circular avatar frame. Holds an image, with the initials behind it. */
function Avatar({
  className,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Root>) {
  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      className={cn(
        "relative flex size-9 shrink-0 overflow-hidden rounded-[var(--radius-control)]",
        "border border-border bg-muted",
        className
      )}
      {...props}
    />
  )
}

/** The photo. Fills the circle and crops square. */
function AvatarImage({
  className,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Image>) {
  return (
    <AvatarPrimitive.Image
      data-slot="avatar-image"
      className={cn("aspect-square size-full object-cover", className)}
      {...props}
    />
  )
}

/**
 * Initials shown while the photo loads or when there is none.
 *
 * Base UI names the hold-back prop `delay` where Radix names it `delayMs`, so
 * this keeps the Radix name and passes it through.
 */
function AvatarFallback({
  className,
  delayMs,
  ...props
}: React.ComponentProps<typeof AvatarPrimitive.Fallback> & {
  /** Milliseconds to wait before the initials appear. */
  delayMs?: number
}) {
  return (
    <AvatarPrimitive.Fallback
      data-slot="avatar-fallback"
      delay={delayMs}
      className={cn(
        "flex size-full items-center justify-center rounded-[var(--radius-control)]",
        "bg-muted text-xs font-semibold text-muted-foreground select-none",
        className
      )}
      {...props}
    />
  )
}

export { Avatar, AvatarImage, AvatarFallback }
