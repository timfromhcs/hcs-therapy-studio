import * as React from "react"
import { CalendarIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine } from "./_shared"
import { Calendar } from "./calendar"

/*
 * Loam DatePicker: a pill field that opens a floating card.
 *
 * The trigger is a form field, so it composes the shared field recipe and
 * stays on the control radius. The calendar floats in the card radius with the
 * floating shadow, so the page below stays flat.
 */

/** Props for the single-date field. */
export interface DatePickerProps {
  value?: Date
  onChange?: (date: Date | undefined) => void
  placeholder?: string
  disabled?: boolean
  /** Forwarded to the trigger so a Label can point at it. */
  id?: string
  className?: string
}

function formatDay(date: Date) {
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

/** Field plus floating calendar for choosing one date. */
export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
  disabled,
  id,
  className,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false)
  const root = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!open) return
    function onPointerDown(event: PointerEvent) {
      if (!(event.target instanceof Node)) return
      if (!root.current?.contains(event.target)) setOpen(false)
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("pointerdown", onPointerDown)
    document.addEventListener("keydown", onKeyDown)
    return () => {
      document.removeEventListener("pointerdown", onPointerDown)
      document.removeEventListener("keydown", onKeyDown)
    }
  }, [open])

  return (
    <div
      ref={root}
      data-slot="date-picker"
      className={cn("relative w-full", className)}
    >
      <button
        type="button"
        id={id}
        disabled={disabled}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "justify-between gap-2 text-left cursor-pointer active:scale-[0.96]",
          "transition-[transform,color,box-shadow,border-color] duration-fast ease-out",
          !value && "text-muted-foreground"
        )}
      >
        <span className="truncate">{value ? formatDay(value) : placeholder}</span>
        <CalendarIcon className="size-4 shrink-0 text-muted-foreground" />
      </button>

      {open ? (
        <div
          data-slot="popover-content"
          role="dialog"
          className={cn(
            "absolute left-0 z-50 mt-2 w-auto p-2",
            "rounded-[var(--radius-card)] border border-border bg-popover text-popover-foreground",
            "[box-shadow:var(--shadow-lg)]"
          )}
        >
          <Calendar
            mode="single"
            autoFocus
            selected={value}
            onSelect={(date) => {
              onChange?.(date)
              setOpen(false)
            }}
          />
        </div>
      ) : null}
    </div>
  )
}
