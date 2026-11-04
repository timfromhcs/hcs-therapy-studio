"use client"

import * as React from "react"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldMultiLine, pressSpring } from "./_shared"

/*
 * Loam TagInput: a field that fills with chips as you type.
 * It grows row by row, so it takes the card tier of the radius scale rather
 * than the pill: a field that can become two lines tall must not be a pill.
 * The chips inside keep the control tier, so the small shapes stay pills.
 */

/** Props for the Loam tag input. */
export interface TagInputProps {
  /** Tags when you drive the control yourself. */
  value?: string[]
  /** Tags the control starts with when it drives itself. */
  defaultValue?: string[]
  /** Runs after every add or remove, with the full new list. */
  onValueChange?: (value: string[]) => void
  placeholder?: string
  /** Stops accepting tags once the list reaches this length. */
  max?: number
  disabled?: boolean
  className?: string
  /** Label for assistive technology on the typing field. */
  "aria-label"?: string
}

/** Field that turns typed text into removable chips on Enter or comma. */
function TagInput({
  value,
  defaultValue,
  onValueChange,
  placeholder = "Add a tag",
  max,
  disabled,
  className,
  "aria-label": ariaLabel = "Add a tag",
}: TagInputProps) {
  const [internal, setInternal] = React.useState<string[]>(defaultValue ?? [])
  const [draft, setDraft] = React.useState("")
  const tags = value ?? internal
  const full = max !== undefined && tags.length >= max

  const commit = (next: string[]) => {
    if (value === undefined) {
      setInternal(next)
    }
    onValueChange?.(next)
  }

  const add = (raw: string) => {
    const tag = raw.trim()
    if (!tag || full || tags.includes(tag)) {
      return
    }
    commit([...tags, tag])
    setDraft("")
  }

  const remove = (tag: string) => {
    commit(tags.filter(item => item !== tag))
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault()
      add(draft)
      return
    }
    if (event.key === "Backspace" && draft === "" && tags.length > 0) {
      remove(tags[tags.length - 1])
    }
  }

  return (
    <div
      data-slot="tag-input"
      data-disabled={disabled ? "" : undefined}
      className={cn(
        formFieldBase,
        formFieldMultiLine,
        "min-h-12 flex-wrap items-center gap-1.5 py-2 resize-none",
        "focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/35",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
    >
      {tags.map(tag => (
        <span
          key={tag}
          data-slot="tag-input-chip"
          className="inline-flex items-center gap-1 rounded-[var(--radius-control)] border border-border bg-secondary px-2.5 py-0.5 text-xs font-semibold text-secondary-foreground"
        >
          {tag}
          <button
            type="button"
            onClick={() => remove(tag)}
            disabled={disabled}
            aria-label={`Remove ${tag}`}
            className={cn(
              "flex cursor-pointer items-center rounded-[var(--radius-control)] text-muted-foreground",
              "transition-[transform,color] duration-fast ease-out",
              pressSpring,
              "hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
              "disabled:pointer-events-none"
            )}
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      <input
        data-slot="tag-input-field"
        value={draft}
        disabled={disabled || full}
        aria-label={ariaLabel}
        placeholder={full ? "" : placeholder}
        onChange={event => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => add(draft)}
        className="min-w-24 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
      />
    </div>
  )
}

export { TagInput }
