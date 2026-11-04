import * as React from "react"
import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/*
 * Loam Button: a flat action pill, on Base UI.
 *
 * The hero variant is the warm near-black fill on a full pill, exactly the
 * app's main call to action. The fill is flat: no gradient, no sheen, no glow.
 * Presence comes from shape, semibold weight and a warm hairline float.
 *
 * Tactility is a spring press (active:scale-[0.96]), not a pressed-in shadow.
 * Loam is paper, so it flexes rather than squashes. Focus is the one cool note
 * in the system: a blue ring offset off the warm page.
 */

const buttonVariants = cva(
  [
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap",
    "text-sm font-semibold leading-none",
    "rounded-[var(--radius-control)] cursor-pointer select-none",
    "transition-[transform,background-color,border-color,box-shadow,color] duration-fast ease-out",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50",
    "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
    "active:scale-[0.96]",
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  ].join(" "),
  {
    variants: {
      variant: {
        // Hero: the warm near-black pill. Hover lifts a hair lighter.
        default:
          "bg-primary text-primary-foreground [box-shadow:var(--shadow-xs)] " +
          "hover:bg-primary/90",
        primary:
          "bg-primary text-primary-foreground [box-shadow:var(--shadow-xs)] " +
          "hover:bg-primary/90",
        // Secondary: the cream pill. Hover deepens the surface, never tints it.
        secondary:
          "bg-secondary text-secondary-foreground [box-shadow:var(--shadow-2xs)] " +
          "hover:bg-accent hover:text-accent-foreground",
        outline:
          "bg-card text-foreground border border-border [box-shadow:var(--shadow-2xs)] " +
          "hover:bg-accent hover:border-foreground/20 hover:text-accent-foreground",
        ghost:
          "bg-transparent text-muted-foreground " +
          "hover:bg-accent hover:text-accent-foreground",
        destructive:
          "bg-destructive text-destructive-foreground [box-shadow:var(--shadow-xs)] " +
          "hover:bg-destructive/90 focus-visible:ring-destructive/40",
        link: "text-foreground underline-offset-4 hover:underline hover:text-pop-blue-ink",
      },
      size: {
        sm: "h-8 gap-1.5 px-4 text-xs",
        default: "h-10 px-5",
        lg: "h-12 px-7 text-base",
        icon: "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

/** Props for the Loam pill button, including its cva variant and size. */
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render the styling onto the single child element instead of a `<button>`. */
  asChild?: boolean
}

/**
 * The Loam action pill: flat fill, full radius, spring press.
 *
 * Base UI has no `asChild`. It takes a `render` element instead, so this keeps
 * the Radix-shaped `asChild` prop and hands the child to `render`.
 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    // SAFETY: `ref` is typed to HTMLButtonElement, which extends HTMLElement.
    // Widening it here lets the same object serve both the `button` branch and
    // the `asChild` clone, whose element type is only known at runtime.
    const shared = {
      "data-slot": "button",
      className: cn(buttonVariants({ variant, size, className })),
      ref: ref as React.Ref<HTMLElement>,
    }

    if (asChild && React.isValidElement(children)) {
      return (
        <ButtonPrimitive
          {...shared}
          nativeButton={false}
          render={children}
          {...props}
        />
      )
    }

    return (
      <ButtonPrimitive {...shared} {...props}>
        {children}
      </ButtonPrimitive>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
