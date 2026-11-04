import * as React from "react"

import { cn } from "@/lib/utils"
import { Label } from "./label"

/*
 * Loam Field: the layout wrapper around one control, its caption and its help
 * text. A field is structure, not a surface, so it takes no radius tier of its
 * own. Only FieldSet draws a card squircle, because a grouped set of fields
 * really is a panel of content.
 */

/** One form row: a caption, a control, and its description or error. */
function Field({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<"div"> & {
  /** `horizontal` puts the control beside its caption, for checkboxes and switches. */
  orientation?: "vertical" | "horizontal"
}) {
  return (
    <div
      data-slot="field"
      data-orientation={orientation}
      role="group"
      className={cn(
        "group/field flex w-full gap-2",
        orientation === "vertical" && "flex-col",
        orientation === "horizontal" && "flex-row items-center",
        "has-[[data-slot=field-error]]:text-destructive",
        className
      )}
      {...props}
    />
  )
}

/** A stack of fields at one rhythm, so a form never spaces itself by hand. */
function FieldGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-group"
      className={cn("flex w-full flex-col gap-5", className)}
      {...props}
    />
  )
}

/** Caption for the field's control. */
function FieldLabel({
  className,
  ...props
}: React.ComponentProps<typeof Label>) {
  return (
    <Label
      data-slot="field-label"
      className={cn(
        "gap-2 group-data-[orientation=horizontal]/field:order-2",
        className
      )}
      {...props}
    />
  )
}

/** Heading inside a field, for a control that needs a title above its help text. */
function FieldTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-title"
      className={cn(
        "text-sm font-semibold leading-snug text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** Help text under the control, in the muted ink. */
function FieldDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="field-description"
      className={cn(
        "text-sm leading-normal text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/** Validation message for the field. Renders nothing when there is none. */
function FieldError({
  className,
  children,
  errors,
  ...props
}: React.ComponentProps<"p"> & {
  /** Validator messages. The first one shows when `children` is empty. */
  errors?: Array<{ message?: string }>
}) {
  const body = children ?? errors?.find(error => error.message)?.message

  if (!body) {
    return null
  }

  return (
    <p
      data-slot="field-error"
      role="alert"
      className={cn("text-sm font-semibold text-destructive", className)}
      {...props}
    >
      {body}
    </p>
  )
}

/** Holds the control plus anything that must sit tight against it. */
function FieldContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-content"
      className={cn("flex min-w-0 flex-1 flex-col gap-1.5", className)}
      {...props}
    />
  )
}

/** A related group of fields on the Loam card squircle. */
function FieldSet({ className, ...props }: React.ComponentProps<"fieldset">) {
  return (
    <fieldset
      data-slot="field-set"
      className={cn(
        "flex w-full flex-col gap-5 rounded-[var(--radius-card)] border border-border bg-card p-6",
        "[box-shadow:var(--shadow-sm)]",
        className
      )}
      {...props}
    />
  )
}

/** Title for a field set. */
function FieldLegend({
  className,
  ...props
}: React.ComponentProps<"legend">) {
  return (
    <legend
      data-slot="field-legend"
      className={cn(
        "mb-1 text-base font-semibold leading-none text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** Hairline rule between field groups, with room to breathe on both sides. */
function FieldSeparator({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-separator"
      role="separator"
      className={cn("my-1 h-px w-full shrink-0 bg-border", className)}
      {...props}
    />
  )
}

export {
  Field,
  FieldContent,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSeparator,
  FieldSet,
  FieldTitle,
}
