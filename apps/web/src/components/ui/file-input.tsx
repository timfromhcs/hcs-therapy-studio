import * as React from "react"
import { Paperclip } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine } from "./_shared"

/*
 * Loam FileInput: the field pill that picks a file.
 * It is a single-line field, so it wears the shared field recipe on the control
 * tier. The browser's own file button becomes a small near-black pill, the same
 * flat fill the primary Button uses, so the two read as one material.
 */

/** File picker on the Loam field pill, with the chosen name beside the button. */
const FileInput = React.forwardRef<
  HTMLInputElement,
  Omit<React.ComponentProps<"input">, "type"> & {
    /** Text shown while no file is chosen. */
    emptyLabel?: string
  }
>(({ className, emptyLabel = "No file chosen", onChange, disabled, ...props }, ref) => {
  const [names, setNames] = React.useState<string[]>([])

  return (
    <div data-slot="file-input" className="flex w-full flex-col gap-2">
      <input
        ref={ref}
        type="file"
        data-slot="file-input-field"
        disabled={disabled}
        onChange={event => {
          setNames(Array.from(event.target.files ?? []).map(file => file.name))
          onChange?.(event)
        }}
        className={cn(
          formFieldBase,
          formFieldSingleLine,
          "cursor-pointer py-0 pl-1.5 pr-4 text-muted-foreground",
          "file:mr-3 file:h-7 file:cursor-pointer file:rounded-[var(--radius-control)]",
          "file:border file:border-primary file:bg-primary file:px-4",
          "file:text-xs file:font-semibold file:text-primary-foreground",
          "file:[box-shadow:var(--shadow-xs)]",
          className
        )}
        {...props}
      />
      <p
        data-slot="file-input-status"
        className="truncate px-4 text-xs text-muted-foreground"
      >
        <Paperclip aria-hidden="true" className="mr-1.5 inline size-3 align-middle" />
        {names.length > 0 ? names.join(", ") : emptyLabel}
      </p>
    </div>
  )
})
FileInput.displayName = "FileInput"

export { FileInput }
