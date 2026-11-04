import * as React from "react"
import { Check, Clock } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine, menuItemBase } from "./_shared"

/*
 * Loam TimePicker: a pill field that opens a floating list of control pills.
 *
 * The list floats in the card radius with the floating shadow. Each row is a
 * control pill, and the chosen time takes the flat near-black primary fill, the
 * same material as the hero button.
 */

/** Props for the time field. */
export interface TimePickerProps {
  /** Selected time as a 24-hour string, for example "09:30". */
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  /** Minutes between options in the list. Defaults to thirty. */
  step?: number
  /** Earliest hour offered. Defaults to midnight. */
  startHour?: number
  /** Last hour offered. Defaults to the final hour of the day. */
  endHour?: number
  disabled?: boolean
  /** Forwarded to the trigger so a Label can point at it. */
  id?: string
  className?: string
}

function buildTimes(step: number, startHour: number, endHour: number) {
  const times: string[] = []
  for (let hour = startHour; hour <= endHour; hour += 1) {
    for (let minute = 0; minute < 60; minute += step) {
      times.push(`${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`)
    }
  }
  return times
}

/** Field plus floating list for choosing a time of day. */
export function TimePicker({
  value,
  onChange,
  placeholder = "Pick a time",
  step = 30,
  startHour = 0,
  endHour = 23,
  disabled,
  id,
  className,
}: TimePickerProps) {
  const [open, setOpen] = React.useState(false)
  const root = React.useRef<HTMLDivElement>(null)
  const times = React.useMemo(
    () => buildTimes(step, startHour, endHour),
    [step, startHour, endHour]
  )

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
      data-slot="time-picker"
      className={cn("relative w-full", className)}
    >
      <button
        type="button"
        id={id}
        disabled={disabled}
        aria-haspopup="listbox"
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
        <span className="truncate tabular-nums">{value ?? placeholder}</span>
        <Clock className="size-4 shrink-0 text-muted-foreground" />
      </button>

      {open ? (
        <div
          data-slot="popover-content"
          role="listbox"
          aria-label="Time"
          className={cn(
            "absolute left-0 z-50 mt-2 max-h-64 w-full min-w-40 overflow-y-auto p-1.5",
            "rounded-[var(--radius-card)] border border-border bg-popover text-popover-foreground",
            "[box-shadow:var(--shadow-lg)]"
          )}
        >
          {times.map((time) => {
            const selected = time === value
            return (
              <button
                key={time}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => {
                  onChange?.(time)
                  setOpen(false)
                }}
                className={cn(
                  menuItemBase,
                  "w-full justify-between tabular-nums cursor-pointer active:scale-[0.96]",
                  "hover:bg-accent hover:text-accent-foreground",
                  selected &&
                    "bg-primary text-primary-foreground font-semibold [box-shadow:var(--shadow-xs)] hover:bg-primary hover:text-primary-foreground"
                )}
              >
                {time}
                {selected ? <Check className="size-3.5" /> : null}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
