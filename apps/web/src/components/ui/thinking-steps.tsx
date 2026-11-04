import * as React from "react"
import { Check, Circle } from "lucide-react"

import { cn } from "@/lib/utils"
import { Spinner } from "./spinner"

/*
 * Loam ThinkingSteps: an agent's progress list, kept deliberately quiet.
 *
 * The list sits on the card tier (1.5rem) with a muted surface. Pending and
 * active steps stay in muted ink. Only a finished step earns colour, and it
 * takes the green pop triad, which is the single place a hue appears here.
 */

/** Where one step sits in its life. */
export type StepStatus = "pending" | "active" | "done"

/** Props for one row in the agent progress list. */
export interface ThinkingStepProps
  extends Omit<React.ComponentProps<"li">, "title"> {
  /** Where this step sits in its life. Defaults to `pending`. */
  status?: StepStatus
  /** The line describing what the agent is doing. */
  label?: React.ReactNode
  /** Optional second line, such as a file path or a count. */
  detail?: React.ReactNode
}

/** One step in the progress list: a status glyph, a label and a detail line. */
function ThinkingStep({
  status = "pending",
  label,
  detail,
  className,
  children,
  ...props
}: ThinkingStepProps) {
  return (
    <li
      data-slot="thinking-step"
      data-status={status}
      className={cn("flex items-start gap-3 py-1", className)}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 flex size-4 shrink-0 items-center justify-center",
          status === "done" ? "text-pop-green-ink" : "text-muted-foreground"
        )}
      >
        {status === "done" ? (
          <Check className="size-3.5" />
        ) : status === "active" ? (
          <Spinner size="sm" className="size-3.5" />
        ) : (
          <Circle className="size-2.5" />
        )}
      </span>

      <span className="flex min-w-0 flex-1 flex-col gap-1">
        {label ? (
          <span
            className={cn(
              "leading-snug",
              status === "done"
                ? "text-pop-green-ink"
                : status === "active"
                  ? "font-semibold text-foreground"
                  : "text-muted-foreground"
            )}
          >
            {label}
          </span>
        ) : null}
        {detail ? (
          <span className="font-mono text-xs text-muted-foreground">
            {detail}
          </span>
        ) : null}
        {children}
      </span>
    </li>
  )
}

/** Props for the source chips under a step. */
export interface ThinkingStepSourcesProps extends React.ComponentProps<"div"> {
  /** The source names or hosts the step read, rendered as small pills. */
  sources?: React.ReactNode[]
}

/** The source chips under a step: control-tier pills in muted ink. */
function ThinkingStepSources({
  sources,
  className,
  children,
  ...props
}: ThinkingStepSourcesProps) {
  return (
    <div
      data-slot="thinking-step-sources"
      className={cn("flex flex-wrap items-center gap-1.5 pt-0.5", className)}
      {...props}
    >
      {sources?.map((source, index) => (
        <span
          key={index}
          className={cn(
            "inline-flex max-w-full items-center truncate",
            "rounded-[var(--radius-control)] border border-border bg-card",
            "px-2 py-0.5 text-xs text-muted-foreground"
          )}
        >
          {source}
        </span>
      ))}
      {children}
    </div>
  )
}

/** Props for the agent progress list. */
export interface ThinkingStepsProps extends React.ComponentProps<"ol"> {
  /** Render the list from data instead of composing `ThinkingStep` children. */
  steps?: Array<{
    id: string
    label: React.ReactNode
    status?: StepStatus
    detail?: React.ReactNode
    sources?: React.ReactNode[]
  }>
}

/** A quiet progress list: muted while working, one green tick when done. */
function ThinkingSteps({
  steps,
  className,
  children,
  ...props
}: ThinkingStepsProps) {
  return (
    <ol
      data-slot="thinking-steps"
      aria-live="polite"
      className={cn(
        "flex w-full list-none flex-col gap-1 rounded-[var(--radius-card)]",
        "border border-border bg-muted px-4 py-3 text-sm",
        className
      )}
      {...props}
    >
      {steps?.map((step) => (
        <ThinkingStep
          key={step.id}
          status={step.status}
          label={step.label}
          detail={step.detail}
        >
          {step.sources?.length ? (
            <ThinkingStepSources sources={step.sources} />
          ) : null}
        </ThinkingStep>
      ))}
      {children}
    </ol>
  )
}

export { ThinkingSteps, ThinkingStep, ThinkingStepSources }
