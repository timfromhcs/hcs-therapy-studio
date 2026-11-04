"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Notification: an inline status card with a dismiss control.
 *
 * Card tier (1.5rem) because it is a small card, bordered on all four sides.
 * Its hue comes from one pop triad, never from a left-edge accent stripe.
 * The dismiss button is an icon pill, so it shares the system press spring.
 */

const notificationVariants = cva(
  "relative flex w-full items-start gap-3 rounded-[var(--radius-card)] border px-5 py-4 text-sm",
  {
    variants: {
      variant: {
        default:
          "border-pop-neutral-border bg-pop-neutral-surface text-pop-neutral-ink",
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

/** Props for the inline notification card, including its pop-triad variant. */
export interface NotificationProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof notificationVariants> {}

/** An inline status card: one pop triad on the whole rim, dismissible. */
function Notification({ className, variant, ...props }: NotificationProps) {
  return (
    <div
      data-slot="notification"
      role="status"
      className={cn(notificationVariants({ variant }), className)}
      {...props}
    />
  )
}

/** The leading icon slot, sized and coloured to match the notification ink. */
function NotificationIcon({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="notification-icon"
      aria-hidden="true"
      className={cn(
        "mt-0.5 flex shrink-0 items-center justify-center text-current [&_svg]:size-4",
        className
      )}
      {...props}
    />
  )
}

/** The text column between the icon and the actions. */
function NotificationContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="notification-content"
      className={cn("flex min-w-0 flex-1 flex-col gap-1", className)}
      {...props}
    />
  )
}

/** The notification headline. */
function NotificationTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="notification-title"
      className={cn("font-semibold leading-none", className)}
      {...props}
    />
  )
}

/** The supporting line under a notification title. */
function NotificationDescription({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="notification-description"
      className={cn("text-sm leading-relaxed text-current/90", className)}
      {...props}
    />
  )
}

/** Trailing slot for action pills, aligned to the top of the card. */
function NotificationActions({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="notification-actions"
      className={cn("flex shrink-0 items-center gap-2", className)}
      {...props}
    />
  )
}

/** The dismiss control: an icon pill that shares the system press spring. */
function NotificationClose({
  className,
  children,
  ...props
}: React.ComponentProps<"button">) {
  return (
    <button
      type="button"
      data-slot="notification-close"
      aria-label="Dismiss notification"
      className={cn(
        "inline-flex size-7 shrink-0 cursor-pointer items-center justify-center",
        "rounded-[var(--radius-control)] text-current/70",
        "transition-[transform,background-color,color] duration-fast ease-out",
        "hover:bg-current/10 hover:text-current",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        pressSpring,
        className
      )}
      {...props}
    >
      {children ?? <X className="size-3.5" />}
    </button>
  )
}

export {
  Notification,
  NotificationIcon,
  NotificationContent,
  NotificationTitle,
  NotificationDescription,
  NotificationActions,
  NotificationClose,
  notificationVariants,
}
