"use client"

import * as React from "react"
import { CalendarRange } from "lucide-react"
import type { DateRange } from "react-day-picker"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine } from "./_shared"
import { Button } from "./button"
import { Calendar } from "./calendar"

/*
 * Loam DataRangePicker: one pill field that opens a floating two-month card.
 *
 * The trigger is a form field on the control radius. The range itself reads as
 * two primary-filled end pills with the accent surface between them, so the
 * selection stays flat like every other Loam fill.
 */

/** Props for the date-range field. */
export interface DataRangePickerProps {
  value?: DateRange
  onChange?: (range: DateRange | undefined) => void
  placeholder?: string
  /** Months shown side by side in the floating card. Defaults to two. */
  numberOfMonths?: number
  disabled?: boolean
  /** Forwarded to the trigger so a Label can point at it. */
  id?: string
  className?: string
}

function formatDay(date: Date) {
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short" })
}

function formatRange(range?: DateRange) {
  if (!range?.from) return null
  if (!range.to) return formatDay(range.from)
  return `${formatDay(range.from)} to ${formatDay(range.to)}`
}

/** Field plus floating calendar for choosing a start and an end date. */
export function DataRangePicker({
  value,
  onChange,
  placeholder = "Pick a date range",
  numberOfMonths = 2,
  disabled,
  id,
  className,
}: DataRangePickerProps) {
  const [open, setOpen] = React.useState(false)
  const root = React.useRef<HTMLDivElement>(null)
  const label = formatRange(value)

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
      data-slot="data-range-picker"
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
          !label && "text-muted-foreground"
        )}
      >
        <span className="truncate">{label ?? placeholder}</span>
        <CalendarRange className="size-4 shrink-0 text-muted-foreground" />
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
            mode="range"
            autoFocus
            numberOfMonths={numberOfMonths}
            selected={value}
            onSelect={(range) => onChange?.(range)}
          />
          <div className="flex items-center justify-between gap-2 px-2 pt-1 pb-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onChange?.(undefined)}
              disabled={!value?.from}
            >
              Clear
            </Button>
            <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
              Done
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}

/** Alias kept so either the file name or the plain-English name imports cleanly. */
export const DateRangePicker = DataRangePicker
