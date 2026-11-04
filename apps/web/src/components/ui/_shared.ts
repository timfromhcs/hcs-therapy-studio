export const formFieldBase =
  "w-full text-sm " +
  "bg-input text-foreground " +
  "border border-border " +
  "placeholder:text-muted-foreground " +
  "transition-[color,box-shadow,border-color] duration-fast ease-out " +
  "hover:border-foreground/20 " +
  "focus-visible:outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/35 " +
  "disabled:cursor-not-allowed disabled:opacity-50"

/** Single-line fields are full pills, matching the control tier. */
export const formFieldSingleLine =
  "flex h-10 items-center rounded-[var(--radius-control)] px-4 py-2"

/** Multi-line fields step back to the card squircle so the shape stays honest. */
export const formFieldMultiLine =
  "flex min-h-21 rounded-[var(--radius-card)] px-4 py-3 resize-y"

/** Card and sheet surface: crisp white, hairline, soft float. */
export const surfaceBase =
  "bg-card text-card-foreground border border-border " +
  "[box-shadow:var(--shadow-sm)]"

/** Floating surfaces (popover, menu, tooltip) share one recipe. */
export const floatingSurfaceBase =
  "bg-popover text-popover-foreground border border-border " +
  "rounded-[var(--radius-card)] [box-shadow:var(--shadow-lg)]"

/** A menu row: pill-ish, warm hover, no tint shift. */
export const menuItemBase =
  "relative flex cursor-default select-none items-center gap-2 " +
  "rounded-[var(--radius-control)] px-3 py-2 text-sm outline-none " +
  "transition-colors duration-fast " +
  "focus:bg-accent focus:text-accent-foreground " +
  "data-[disabled]:pointer-events-none data-[disabled]:opacity-50"

/**
 * The press. Every interactive control shares this spring so the whole system
 * feels like one material under the cursor.
 */
export const pressSpring = "active:scale-[0.96]"

/**
 * The filled-control treatment, lifted from the primary Button so a checked
 * checkbox, a switch track, a radio dot and a slider range all read as the
 * same flat near-black material as the hero pill.
 */
export const filledControl =
  "bg-primary text-primary-foreground border-primary " +
  "[box-shadow:var(--shadow-xs)]"

/**
 * Base UI marks a highlighted menu row with data-highlighted, where Radix
 * moves DOM focus. This adds the same warm hover to the Base UI state so both
 * copies of a menu look identical.
 */
export const menuItemHighlight =
  "data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground"
