"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Toast: a floating surface.
 *
 * A toast leaves the page, so it takes the popover surface, the card radius
 * (1.5rem) and the floating shadow token. Its own primitives are plain
 * elements rather than Radix, so the set ships without an extra dependency.
 */

const toastVariants = cva(
  [
    "group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden",
    "rounded-[var(--radius-card)] border p-4 pr-10",
    "[box-shadow:var(--shadow-lg)]",
    "transition-[transform,opacity] duration-base ease-out",
    "data-[state=closed]:opacity-0 data-[state=closed]:translate-y-1",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "border-border bg-popover text-popover-foreground",
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

/** Props for one floating toast, including its pop-triad variant. */
export interface ToastProps
  extends Omit<React.ComponentProps<"li">, "title">,
    VariantProps<typeof toastVariants> {
  /** Drives the exit transition when the queue starts removing this toast. */
  open?: boolean
}

/** The element a toast action pill must be, so the queue can carry one. */
export type ToastActionElement = React.ReactElement

/** Wraps the app so toasts have an owner. Loam keeps it dependency free. */
function ToastProvider({ children }: { children?: React.ReactNode }) {
  return <>{children}</>
}

/** The fixed stack toasts render into, bottom right on desktop, top on phones. */
function ToastViewport({ className, ...props }: React.ComponentProps<"ol">) {
  return (
    <ol
      data-slot="toast-viewport"
      className={cn(
        "pointer-events-none fixed top-0 z-100 flex max-h-screen w-full flex-col gap-3 p-4",
        "sm:bottom-0 sm:right-0 sm:top-auto sm:w-full sm:max-w-sm sm:flex-col-reverse",
        className
      )}
      {...props}
    />
  )
}

/** One floating toast: popover surface, card radius, floating shadow. */
function Toast({ className, variant, open = true, ...props }: ToastProps) {
  return (
    <li
      data-slot="toast"
      data-state={open ? "open" : "closed"}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    />
  )
}

/** The toast headline. */
function ToastTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="toast-title"
      className={cn("text-sm font-semibold leading-none", className)}
      {...props}
    />
  )
}

/** The supporting line under a toast title. */
function ToastDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="toast-description"
      className={cn("text-sm leading-relaxed text-current/90", className)}
      {...props}
    />
  )
}

/** The trailing action pill inside a toast. */
function ToastAction({ className, ...props }: React.ComponentProps<"button">) {
  return (
    <button
      type="button"
      data-slot="toast-action"
      className={cn(
        "inline-flex h-8 shrink-0 cursor-pointer items-center justify-center",
        "rounded-[var(--radius-control)] border border-border bg-card px-4",
        "text-xs font-semibold text-foreground",
        "transition-[transform,background-color,border-color,color] duration-fast ease-out",
        "hover:bg-accent hover:text-accent-foreground hover:border-foreground/20",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        pressSpring,
        className
      )}
      {...props}
    />
  )
}

/** The dismiss control, parked in the toast's top right corner. */
function ToastClose({
  className,
  children,
  ...props
}: React.ComponentProps<"button">) {
  return (
    <button
      type="button"
      data-slot="toast-close"
      aria-label="Dismiss notification"
      className={cn(
        "absolute right-2 top-2 inline-flex size-7 cursor-pointer items-center justify-center",
        "rounded-[var(--radius-control)] text-current/60",
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
  Toast,
  ToastProvider,
  ToastViewport,
  ToastTitle,
  ToastDescription,
  ToastAction,
  ToastClose,
  toastVariants,
}
