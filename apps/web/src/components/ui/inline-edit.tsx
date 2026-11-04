"use client"

import * as React from "react"
import { Check, Pencil, X } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine, pressSpring } from "./_shared"

/*
 * Loam InlineEdit: text that becomes a field when you press it.
 * Resting, it is a ghost pill that deepens on hover, exactly like a ghost
 * Button. Editing, it becomes the single-line field pill with the shared field
 * recipe, so the shape never jumps between the two states.
 */

/** Props for the Loam inline edit. */
export interface InlineEditProps {
  /** Text when you drive the control yourself. */
  value?: string
  /** Text the control starts with when it drives itself. */
  defaultValue?: string
  /** Runs when the edit is saved. */
  onValueChange?: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  /** Label for assistive technology on the edit field. */
  "aria-label"?: string
}

/** Press the text to edit it in place, then save or cancel. */
function InlineEdit({
  value,
  defaultValue,
  onValueChange,
  placeholder = "Add a value",
  disabled,
  className,
  "aria-label": ariaLabel = "Edit value",
}: InlineEditProps) {
  const [internal, setInternal] = React.useState(defaultValue ?? "")
  const text = value ?? internal
  const [editing, setEditing] = React.useState(false)
  const [draft, setDraft] = React.useState(text)
  const fieldRef = React.useRef<HTMLInputElement | null>(null)

  React.useEffect(() => {
    if (editing) {
      fieldRef.current?.focus()
      fieldRef.current?.select()
    }
  }, [editing])

  const start = () => {
    setDraft(text)
    setEditing(true)
  }

  const save = () => {
    if (value === undefined) {
      setInternal(draft)
    }
    onValueChange?.(draft)
    setEditing(false)
  }

  const cancel = () => {
    setDraft(text)
    setEditing(false)
  }

  const actionClass = cn(
    "flex size-8 shrink-0 cursor-pointer items-center justify-center",
    "rounded-[var(--radius-control)] text-muted-foreground",
    "transition-[transform,background-color,color] duration-fast ease-out",
    pressSpring,
    "hover:bg-accent hover:text-accent-foreground",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
  )

  if (!editing) {
    return (
      <div
        data-slot="inline-edit"
        className={cn("flex w-full items-center gap-1", className)}
      >
        <button
          type="button"
          data-slot="inline-edit-trigger"
          onClick={start}
          disabled={disabled}
          className={cn(
            "flex h-10 min-w-0 flex-1 items-center gap-2 rounded-[var(--radius-control)] px-4 text-left text-sm",
            "cursor-text border border-transparent text-foreground",
            "transition-[transform,background-color,border-color,color] duration-fast ease-out",
            pressSpring,
            "hover:border-border hover:bg-accent hover:text-accent-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:pointer-events-none disabled:opacity-50",
            !text && "text-muted-foreground"
          )}
        >
          <span className="truncate">{text || placeholder}</span>
          <Pencil aria-hidden="true" className="ml-auto size-3.5 shrink-0 text-muted-foreground" />
        </button>
      </div>
    )
  }

  return (
    <div
      data-slot="inline-edit"
      className={cn("flex w-full items-center gap-1", className)}
    >
      <input
        ref={fieldRef}
        data-slot="inline-edit-field"
        value={draft}
        aria-label={ariaLabel}
        placeholder={placeholder}
        onChange={event => setDraft(event.target.value)}
        onKeyDown={event => {
          if (event.key === "Enter") {
            event.preventDefault()
            save()
          }
          if (event.key === "Escape") {
            event.preventDefault()
            cancel()
          }
        }}
        className={cn(formFieldBase, formFieldSingleLine, "flex-1")}
      />
      <button
        type="button"
        data-slot="inline-edit-save"
        onClick={save}
        aria-label="Save"
        className={actionClass}
      >
        <Check className="size-4" strokeWidth={3} />
      </button>
      <button
        type="button"
        data-slot="inline-edit-cancel"
        onClick={cancel}
        aria-label="Cancel"
        className={actionClass}
      >
        <X className="size-4" />
      </button>
    </div>
  )
}

export { InlineEdit }
