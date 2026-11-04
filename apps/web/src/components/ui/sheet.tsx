import * as React from "react"
import { Dialog as SheetPrimitive } from "@base-ui/react/dialog"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"
import { pressSpring } from "./_shared"

/*
 * Loam Sheet: the panel tier, anchored to one edge.
 *
 * A sheet is a panel, so it takes the panel radius (2rem) and the deepest
 * float. Only the inner corners round, because a corner that meets the
 * viewport edge has nothing to round against.
 */

/** Root of the edge sheet. */
function Sheet({ ...props }: React.ComponentProps<typeof SheetPrimitive.Root>) {
  return <SheetPrimitive.Root {...props} />
}

/** The control that opens the sheet. */
function SheetTrigger({
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Trigger>) {
  return <SheetPrimitive.Trigger data-slot="sheet-trigger" {...props} />
}

/** Any control inside the sheet that closes it. */
function SheetClose({
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Close>) {
  return <SheetPrimitive.Close data-slot="sheet-close" {...props} />
}

/**
 * Renders the sheet into a portal at the end of the body.
 *
 * Base UI's portal takes no arbitrary DOM props, so this one carries no
 * data-slot where the Radix copy has one.
 */
function SheetPortal({
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Portal>) {
  return <SheetPrimitive.Portal {...props} />
}

/**
 * The warm scrim behind the sheet.
 *
 * Base UI calls this part Backdrop and fades it with a CSS transition between
 * `data-starting-style` and `data-ending-style`.
 */
function SheetOverlay({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Backdrop>) {
  return (
    <SheetPrimitive.Backdrop
      data-slot="sheet-overlay"
      className={cn(
        "fixed inset-0 z-50 bg-foreground/30",
        "transition-opacity duration-base ease-out",
        "data-[starting-style]:opacity-0 data-[ending-style]:opacity-0",
        className
      )}
      {...props}
    />
  )
}

/**
 * The sheet panel, sliding in from the chosen edge.
 *
 * Base UI calls this part Popup, so the slide is a transform transition
 * between its starting and ending styles rather than the Radix slide
 * utilities. The `side` prop and the class list are unchanged.
 */
function SheetContent({
  className,
  children,
  side = "right",
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Popup> & {
  /** Which viewport edge the sheet is anchored to. */
  side?: "top" | "right" | "bottom" | "left"
}) {
  return (
    <SheetPortal>
      <SheetOverlay />
      <SheetPrimitive.Popup
        data-slot="sheet-content"
        className={cn(
          "fixed z-50 flex flex-col gap-4 p-6 outline-none",
          "bg-popover text-popover-foreground border border-border",
          "[box-shadow:var(--shadow-xl)]",
          "transition-transform duration-base ease-out",
          side === "right" &&
            "inset-y-0 right-0 h-full w-3/4 rounded-l-[var(--radius-panel)] sm:max-w-sm data-[starting-style]:translate-x-full data-[ending-style]:translate-x-full",
          side === "left" &&
            "inset-y-0 left-0 h-full w-3/4 rounded-r-[var(--radius-panel)] sm:max-w-sm data-[starting-style]:-translate-x-full data-[ending-style]:-translate-x-full",
          side === "top" &&
            "inset-x-0 top-0 h-auto rounded-b-[var(--radius-panel)] data-[starting-style]:-translate-y-full data-[ending-style]:-translate-y-full",
          side === "bottom" &&
            "inset-x-0 bottom-0 h-auto rounded-t-[var(--radius-panel)] data-[starting-style]:translate-y-full data-[ending-style]:translate-y-full",
          className
        )}
        {...props}
      >
        {children}
        <SheetPrimitive.Close
          className={cn(
            "absolute top-5 right-5 inline-flex size-8 items-center justify-center",
            "rounded-[var(--radius-control)] text-muted-foreground",
            "transition-[transform,background-color,color] duration-fast ease-out",
            "hover:bg-accent hover:text-accent-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:pointer-events-none",
            pressSpring
          )}
        >
          <X className="size-4" />
          <span className="sr-only">Close</span>
        </SheetPrimitive.Close>
      </SheetPrimitive.Popup>
    </SheetPortal>
  )
}

/** Title and description stack at the top of the sheet. */
function SheetHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-header"
      className={cn("flex flex-col gap-1.5 pr-10", className)}
      {...props}
    />
  )
}

/** Footer pinned to the bottom of the sheet, holding the action pills. */
function SheetFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-footer"
      className={cn("mt-auto flex flex-col gap-2", className)}
      {...props}
    />
  )
}

/** The sheet title, announced as its accessible name. */
function SheetTitle({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Title>) {
  return (
    <SheetPrimitive.Title
      data-slot="sheet-title"
      className={cn("font-semibold text-foreground", className)}
      {...props}
    />
  )
}

/** Supporting line under the sheet title. */
function SheetDescription({
  className,
  ...props
}: React.ComponentProps<typeof SheetPrimitive.Description>) {
  return (
    <SheetPrimitive.Description
      data-slot="sheet-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetPortal,
  SheetOverlay,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}
