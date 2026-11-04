"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import {
  formFieldBase,
  formFieldMultiLine,
  formFieldSingleLine,
  pressSpring,
} from "./_shared"

/*
 * Loam InputGroup: one field that holds a control plus its addons.
 * The group is the field, so the group wears the shared field recipe: the
 * control tier when it holds a single line, the card tier when it holds a
 * textarea. The inner input draws nothing, so the row keeps one outline.
 */

/** The field shell. Put addons and one input or textarea inside it. */
function InputGroup({
  className,
  variant = "single",
  ...props
}: React.ComponentProps<"div"> & {
  /** `multi` steps the shell back to the card squircle for a textarea. */
  variant?: "single" | "multi"
}) {
  return (
    <div
      data-slot="input-group"
      data-variant={variant}
      role="group"
      className={cn(
        formFieldBase,
        variant === "single" ? formFieldSingleLine : formFieldMultiLine,
        "gap-2 px-3",
        variant === "multi" && "min-h-24 flex-col items-stretch gap-1.5 py-3",
        "focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/35",
        "has-[input:disabled]:cursor-not-allowed has-[input:disabled]:opacity-50",
        className
      )}
      {...props}
    />
  )
}

/** The text field inside a group. It borrows the shell's surface and ring. */
function InputGroupInput({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      data-slot="input-group-input"
      className={cn(
        "min-w-0 flex-1 bg-transparent px-1 text-sm text-foreground outline-none",
        "placeholder:text-muted-foreground",
        "disabled:cursor-not-allowed",
        className
      )}
      {...props}
    />
  )
}

/** The multi-line field inside a card-tier group. */
function InputGroupTextarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="input-group-textarea"
      className={cn(
        "min-h-16 w-full flex-1 resize-none bg-transparent px-1 text-sm text-foreground outline-none",
        "placeholder:text-muted-foreground",
        "disabled:cursor-not-allowed",
        className
      )}
      {...props}
    />
  )
}

/** Holds an icon, a unit or a button at one end of the group. */
function InputGroupAddon({
  className,
  align = "start",
  ...props
}: React.ComponentProps<"div"> & {
  /** Which end of the shell the addon sits at. */
  align?: "start" | "end"
}) {
  return (
    <div
      data-slot="input-group-addon"
      data-align={align}
      className={cn(
        "flex shrink-0 items-center gap-1.5 text-muted-foreground",
        align === "end" && "order-last",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

/** Static text inside an addon, such as a prefix or a unit. */
function InputGroupText({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="input-group-text"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

/** A small ghost pill action inside the group, such as apply or clear. */
function InputGroupButton({
  className,
  type = "button",
  ...props
}: React.ComponentProps<"button">) {
  return (
    <button
      type={type}
      data-slot="input-group-button"
      className={cn(
        "inline-flex h-7 shrink-0 cursor-pointer items-center justify-center gap-1.5",
        "rounded-[var(--radius-control)] px-3 text-xs font-semibold text-muted-foreground",
        "transition-[transform,background-color,color] duration-fast ease-out",
        pressSpring,
        "hover:bg-accent hover:text-accent-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:opacity-50",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

export {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
  InputGroupText,
  InputGroupTextarea,
}
