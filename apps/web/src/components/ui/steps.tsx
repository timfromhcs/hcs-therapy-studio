import * as React from "react"
import { CheckIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/*
 * Loam Steps: numbered pills joined by a hairline.
 *
 * The indicator is a small circle at the control tier, and a done or current
 * step takes the primary button's flat near-black fill, so the progress marker
 * and the hero pill read as the same material. The rail between steps is the
 * same warm border hairline every card rim uses.
 */

/** The step state a caller can set, or Steps can derive from its own index. */
type StepState = "complete" | "current" | "upcoming"

const StepsContext = React.createContext<{
  orientation: "horizontal" | "vertical"
}>({ orientation: "horizontal" })

const StepContext = React.createContext<{ state: StepState }>({
  state: "upcoming",
})

/** The ordered list of steps, laid out in a row or a column. */
function Steps({
  className,
  orientation = "horizontal",
  ...props
}: React.ComponentProps<"ol"> & {
  /** Row for a wizard header, column for a checklist. */
  orientation?: "horizontal" | "vertical"
}) {
  return (
    <StepsContext.Provider value={{ orientation }}>
      <ol
        data-slot="steps"
        data-orientation={orientation}
        className={cn(
          "flex w-full",
          orientation === "horizontal"
            ? "flex-row items-center gap-3"
            : "flex-col gap-4",
          className
        )}
        {...props}
      />
    </StepsContext.Provider>
  )
}

/** One step. Its state colours the indicator and the label beneath it. */
function Step({
  className,
  state = "upcoming",
  ...props
}: React.ComponentProps<"li"> & {
  /** Where this step sits in the run: done, in hand, or still ahead. */
  state?: StepState
}) {
  const { orientation } = React.useContext(StepsContext)

  return (
    <StepContext.Provider value={{ state }}>
      <li
        data-slot="step"
        data-state={state}
        className={cn(
          "flex min-w-0",
          orientation === "horizontal"
            ? "flex-row items-center gap-3"
            : "flex-row items-start gap-3",
          className
        )}
        {...props}
      />
    </StepContext.Provider>
  )
}

/** The numbered circle. Done and current steps take the flat primary fill. */
function StepIndicator({
  className,
  children,
  ...props
}: React.ComponentProps<"span">) {
  const { state } = React.useContext(StepContext)

  return (
    <span
      data-slot="step-indicator"
      data-state={state}
      aria-hidden="true"
      className={cn(
        "flex size-8 shrink-0 items-center justify-center",
        "rounded-[var(--radius-control)] text-xs font-semibold",
        "transition-colors duration-fast ease-out",
        state === "upcoming" &&
          "border border-border bg-card text-muted-foreground",
        (state === "current" || state === "complete") &&
          "bg-primary text-primary-foreground [box-shadow:var(--shadow-xs)]",
        "[&_svg]:size-4 [&_svg]:shrink-0",
        className
      )}
      {...props}
    >
      {state === "complete" ? (children ?? <CheckIcon />) : children}
    </span>
  )
}

/** The step name. It is the line the reader scans, so it stays semibold. */
function StepTitle({ className, ...props }: React.ComponentProps<"span">) {
  const { state } = React.useContext(StepContext)

  return (
    <span
      data-slot="step-title"
      className={cn(
        "block text-sm font-semibold",
        state === "upcoming" ? "text-muted-foreground" : "text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** A supporting line under a step title. */
function StepDescription({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="step-description"
      className={cn("block text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

/** The text block beside the indicator, holding the title and the detail. */
function StepContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="step-content"
      className={cn("flex min-w-0 flex-col gap-0.5", className)}
      {...props}
    />
  )
}

/** The hairline rail between two steps. */
function StepSeparator({ className, ...props }: React.ComponentProps<"span">) {
  const { orientation } = React.useContext(StepsContext)

  return (
    <span
      data-slot="step-separator"
      aria-hidden="true"
      className={cn(
        "bg-border",
        orientation === "horizontal"
          ? "h-px min-w-6 flex-1"
          : "ml-4 min-h-6 w-px",
        className
      )}
      {...props}
    />
  )
}

export {
  Steps,
  Step,
  StepIndicator,
  StepTitle,
  StepDescription,
  StepContent,
  StepSeparator,
}
