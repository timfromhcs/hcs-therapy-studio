"use client"

import * as React from "react"
import { Eye, EyeOff } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine, pressSpring } from "./_shared"

/*
 * Loam PasswordInput: the field pill with a reveal toggle.
 * It is a single-line field, so it wears the shared field recipe on the control
 * tier. The toggle sits inside the pill's right padding as a ghost icon, so the
 * field keeps one outline instead of two.
 */

/** Password field with a button that reveals or hides the characters. */
const PasswordInput = React.forwardRef<
  HTMLInputElement,
  Omit<React.ComponentProps<"input">, "type">
>(({ className, disabled, ...props }, ref) => {
  const [visible, setVisible] = React.useState(false)
  const Icon = visible ? EyeOff : Eye

  return (
    <div data-slot="password-input" className="relative w-full">
      <input
        ref={ref}
        type={visible ? "text" : "password"}
        data-slot="password-input-field"
        disabled={disabled}
        className={cn(formFieldBase, formFieldSingleLine, "pr-12", className)}
        {...props}
      />
      <button
        type="button"
        data-slot="password-input-toggle"
        onClick={() => setVisible(current => !current)}
        disabled={disabled}
        aria-label={visible ? "Hide password" : "Show password"}
        className={cn(
          "absolute right-1.5 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center",
          "cursor-pointer rounded-[var(--radius-control)] text-muted-foreground",
          "transition-[transform,background-color,color] duration-fast ease-out",
          pressSpring,
          "hover:bg-accent hover:text-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:pointer-events-none disabled:opacity-50"
        )}
      >
        <Icon className="size-4" />
      </button>
    </div>
  )
})
PasswordInput.displayName = "PasswordInput"

export { PasswordInput }
