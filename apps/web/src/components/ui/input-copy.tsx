import * as React from "react"
import { Check, Copy } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine, pressSpring } from "./_shared"

/*
 * Loam InputCopy: a read-only field pill with a copy button.
 * It is a single-line field, so it wears the shared field recipe on the control
 * tier. The value is mono, because the thing you copy is usually a key or a
 * link, and the button lives inside the pill's padding.
 */

/** Read-only field that copies its value to the clipboard on one press. */
const InputCopy = React.forwardRef<
  HTMLInputElement,
  Omit<React.ComponentProps<"input">, "value" | "readOnly" | "onCopy"> & {
    /** The text shown in the field and written to the clipboard. */
    value: string
    /** Runs after the value reaches the clipboard. */
    onCopy?: (value: string) => void
  }
>(({ className, value, onCopy, disabled, ...props }, ref) => {
  const [copied, setCopied] = React.useState(false)
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  React.useEffect(
    () => () => {
      if (timer.current) {
        clearTimeout(timer.current)
      }
    },
    []
  )

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      return
    }
    onCopy?.(value)
    setCopied(true)
    if (timer.current) {
      clearTimeout(timer.current)
    }
    timer.current = setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div data-slot="input-copy" className="relative w-full">
      <input
        ref={ref}
        readOnly
        value={value}
        data-slot="input-copy-field"
        disabled={disabled}
        onFocus={event => event.currentTarget.select()}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "pr-12 font-mono text-xs",
          className
        )}
        {...props}
      />
      <button
        type="button"
        data-slot="input-copy-button"
        onClick={copy}
        disabled={disabled}
        aria-label={copied ? "Copied" : "Copy to clipboard"}
        className={cn(
          "absolute right-1.5 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center",
          "cursor-pointer rounded-[var(--radius-control)] text-muted-foreground",
          "transition-[transform,background-color,color] duration-fast ease-out",
          pressSpring,
          "hover:bg-accent hover:text-accent-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:pointer-events-none disabled:opacity-50",
          copied && "text-pop-green-ink"
        )}
      >
        {copied ? (
          <Check className="size-4" strokeWidth={3} />
        ) : (
          <Copy className="size-4" />
        )}
      </button>
    </div>
  )
})
InputCopy.displayName = "InputCopy"

export { InputCopy }
