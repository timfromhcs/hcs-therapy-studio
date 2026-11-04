import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Cursor: the pointer with a name label used in the presence demos.
 *
 * The typed bubble is a small card, so it takes the card radius (1.5rem) and
 * the card float. The name chip under the pointer is a control pill. Both stay
 * flat, because Loam's presence is paper, not glass.
 */

/** Props for the presence cursor. */
export interface CursorProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** The text the cursor types out into its bubble. */
  text: string
  /** The name shown on the chip beside the pointer dot. */
  label?: string
  /** Colour of the pointer dot and the caret. Defaults to the primary ink. */
  color?: string
  /** Milliseconds per character. Defaults to 60. */
  speed?: number
  /** Milliseconds to wait before typing starts. Defaults to 500. */
  delay?: number
  /** Retype the text from the start once it finishes. */
  loop?: boolean
}

/** A presence cursor: a typed bubble above a coloured dot and a name chip. */
function Cursor({
  text,
  label,
  color = "var(--primary)",
  speed = 60,
  delay = 500,
  loop = false,
  className,
  ...props
}: CursorProps) {
  const [typed, setTyped] = React.useState("")
  const [isTyping, setIsTyping] = React.useState(false)

  React.useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>
    let index = 0

    const start = () => {
      setIsTyping(true)
      setTyped("")
      index = 0

      const typeChar = () => {
        if (index < text.length) {
          setTyped(text.slice(0, index + 1))
          index += 1
          timeout = setTimeout(typeChar, speed)
          return
        }

        setIsTyping(false)
        if (loop) {
          timeout = setTimeout(() => {
            setTyped("")
            timeout = setTimeout(start, delay)
          }, 2000)
        }
      }

      timeout = setTimeout(typeChar, 100)
    }

    timeout = setTimeout(start, delay)
    return () => clearTimeout(timeout)
  }, [text, speed, delay, loop])

  return (
    <span
      data-slot="cursor"
      className={cn("relative inline-flex flex-col items-start gap-2", className)}
      {...props}
    >
      {isTyping || typed ? (
        <span
          className={cn(
            "inline-flex min-h-9 items-center rounded-[var(--radius-card)]",
            "border border-border bg-card px-4 py-2 text-sm text-card-foreground",
            "[box-shadow:var(--shadow-sm)]"
          )}
        >
          <span>{typed}</span>
          <span
            aria-hidden="true"
            className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse align-middle"
            style={{ backgroundColor: color }}
          />
        </span>
      ) : null}

      {label ? (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-[var(--radius-control)]",
            "border border-border bg-card px-2.5 py-1",
            "text-xs font-semibold text-muted-foreground"
          )}
        >
          <span
            aria-hidden="true"
            className="size-2 shrink-0 rounded-full"
            style={{ backgroundColor: color }}
          />
          {label}
        </span>
      ) : null}
    </span>
  )
}

export { Cursor }
