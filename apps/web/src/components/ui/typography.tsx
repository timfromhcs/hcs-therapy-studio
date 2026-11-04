import * as React from "react"

import { cn } from "@/lib/utils"

/*
 * Loam Typography: the prose scale, carried by size, weight and colour.
 *
 * Each step is at least a quarter larger than the one below it, so a heading is
 * never mistaken for the line under it. Radius appears only on the code pill
 * and the quote card, because prose itself has no surface.
 */

/** Every step of the Loam prose scale, used by the Typography variant prop. */
export type TypographyVariant =
  | "h1"
  | "h2"
  | "h3"
  | "h4"
  | "p"
  | "lead"
  | "large"
  | "small"
  | "muted"
  | "blockquote"
  | "inlineCode"
  | "list"

/** Page title: the largest step, tight tracking, semibold. */
function TypographyH1({ className, ...props }: React.ComponentProps<"h1">) {
  return (
    <h1
      data-slot="typography-h1"
      className={cn(
        "scroll-m-20 text-5xl font-semibold tracking-tight text-foreground text-balance",
        className
      )}
      {...props}
    />
  )
}

/** Section heading: a clear step down from the page title. */
function TypographyH2({ className, ...props }: React.ComponentProps<"h2">) {
  return (
    <h2
      data-slot="typography-h2"
      className={cn(
        "scroll-m-20 text-3xl font-semibold tracking-tight text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** Subsection heading. */
function TypographyH3({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      data-slot="typography-h3"
      className={cn(
        "scroll-m-20 text-2xl font-semibold tracking-tight text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** The smallest heading, still clearly above body text. */
function TypographyH4({ className, ...props }: React.ComponentProps<"h4">) {
  return (
    <h4
      data-slot="typography-h4"
      className={cn("scroll-m-20 text-lg font-semibold text-foreground", className)}
      {...props}
    />
  )
}

/** Body paragraph. Spaces itself when it follows another paragraph. */
function TypographyP({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="typography-p"
      className={cn("leading-7 text-foreground [&:not(:first-child)]:mt-5", className)}
      {...props}
    />
  )
}

/** The opening line under a title, larger and quieter than body text. */
function TypographyLead({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="typography-lead"
      className={cn("text-xl leading-8 text-muted-foreground", className)}
      {...props}
    />
  )
}

/** One emphasised line at body colour, a step above the paragraph. */
function TypographyLarge({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="typography-large"
      className={cn("text-lg font-semibold text-foreground", className)}
      {...props}
    />
  )
}

/** Fine print that still needs to be read. */
function TypographySmall({ className, ...props }: React.ComponentProps<"small">) {
  return (
    <small
      data-slot="typography-small"
      className={cn("text-sm font-semibold leading-none text-foreground", className)}
      {...props}
    />
  )
}

/** Supporting line that should recede. */
function TypographyMuted({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="typography-muted"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

/** A quotation, held in a card squircle rather than by a stripe. */
function TypographyBlockquote({ className, ...props }: React.ComponentProps<"blockquote">) {
  return (
    <blockquote
      data-slot="typography-blockquote"
      className={cn(
        "mt-5 rounded-[var(--radius-card)] border border-border bg-muted px-5 py-4",
        "text-base italic text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

/** A code fragment inside a sentence, on the mono pill. */
function TypographyInlineCode({ className, ...props }: React.ComponentProps<"code">) {
  return (
    <code
      data-slot="typography-inline-code"
      className={cn(
        "rounded-[var(--radius-control)] border border-border bg-muted px-1.5 py-0.5",
        "font-mono text-sm font-semibold text-foreground",
        className
      )}
      {...props}
    />
  )
}

/** A bulleted list at body size. */
function TypographyList({ className, ...props }: React.ComponentProps<"ul">) {
  return (
    <ul
      data-slot="typography-list"
      className={cn("my-5 ml-6 list-disc text-foreground [&>li]:mt-2", className)}
      {...props}
    />
  )
}

/** Props for the single component that picks a prose step by name. */
export interface TypographyProps extends React.HTMLAttributes<HTMLElement> {
  /** Which step of the scale to render. Defaults to the body paragraph. */
  variant?: TypographyVariant
}

/** Renders one step of the prose scale, chosen by the variant prop. */
function Typography({ variant = "p", ...props }: TypographyProps) {
  switch (variant) {
    case "h1":
      return <TypographyH1 {...props} />
    case "h2":
      return <TypographyH2 {...props} />
    case "h3":
      return <TypographyH3 {...props} />
    case "h4":
      return <TypographyH4 {...props} />
    case "lead":
      return <TypographyLead {...props} />
    case "large":
      return <TypographyLarge {...props} />
    case "small":
      return <TypographySmall {...props} />
    case "muted":
      return <TypographyMuted {...props} />
    case "blockquote":
      return <TypographyBlockquote {...props} />
    case "inlineCode":
      return <TypographyInlineCode {...props} />
    case "list":
      return <TypographyList {...props} />
    default:
      return <TypographyP {...props} />
  }
}

/** Short alias for TypographyH1. */
const H1 = TypographyH1
/** Short alias for TypographyH2. */
const H2 = TypographyH2
/** Short alias for TypographyH3. */
const H3 = TypographyH3
/** Short alias for TypographyH4. */
const H4 = TypographyH4
/** Short alias for TypographyP. */
const P = TypographyP
/** Short alias for TypographyLead. */
const Lead = TypographyLead
/** Short alias for TypographyLarge. */
const Large = TypographyLarge
/** Short alias for TypographySmall. */
const Small = TypographySmall
/** Short alias for TypographyMuted. */
const Muted = TypographyMuted
/** Short alias for TypographyBlockquote. */
const Blockquote = TypographyBlockquote
/** Short alias for TypographyInlineCode. */
const InlineCode = TypographyInlineCode
/** Short alias for TypographyList. */
const List = TypographyList

export {
  Typography,
  TypographyH1,
  TypographyH2,
  TypographyH3,
  TypographyH4,
  TypographyP,
  TypographyLead,
  TypographyLarge,
  TypographySmall,
  TypographyMuted,
  TypographyBlockquote,
  TypographyInlineCode,
  TypographyList,
  H1,
  H2,
  H3,
  H4,
  P,
  Lead,
  Large,
  Small,
  Muted,
  Blockquote,
  InlineCode,
  List,
}
