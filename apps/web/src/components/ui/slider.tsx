import * as React from "react"
import { Slider as SliderPrimitive } from "@base-ui/react/slider"

import { cn } from "@/lib/utils"

/*
 * Loam Slider: a near-white track whose filled range is the flat near-black
 * primary, matching the Button. The thumb is a white knob on a warm hairline,
 * carrying the same soft float as a card.
 */

/**
 * A slider whose range fill matches the Loam primary button.
 *
 * Base UI renders one thumb per value rather than accepting thumbs as
 * children, so this reads the value list and maps a thumb over it, and it adds
 * the Control part Base UI needs between the root and the track.
 */
const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, defaultValue, value, min = 0, max = 100, ...props }, ref) => {
  const _values = Array.isArray(value)
    ? value
    : Array.isArray(defaultValue)
      ? defaultValue
      : [min, max]

  return (
    <SliderPrimitive.Root
      ref={ref}
      data-slot="slider"
      thumbAlignment="edge"
      defaultValue={defaultValue}
      value={value}
      min={min}
      max={max}
      className={cn(
        "relative w-full touch-none select-none",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      {...props}
    >
      <SliderPrimitive.Control className="relative flex w-full touch-none select-none items-center">
        <SliderPrimitive.Track
          data-slot="slider-track"
          className="relative h-1.5 w-full grow overflow-hidden rounded-[var(--radius-control)] border border-border bg-input"
        >
          <SliderPrimitive.Indicator
            data-slot="slider-range"
            className="absolute h-full bg-primary"
          />
        </SliderPrimitive.Track>
        {Array.from({ length: _values.length }, (_, index) => (
          <SliderPrimitive.Thumb
            key={index}
            data-slot="slider-thumb"
            className={cn(
              "block size-4 shrink-0 rounded-[var(--radius-control)] border border-border bg-card",
              "[box-shadow:var(--shadow-sm)]",
              "cursor-grab transition-[box-shadow,transform] duration-fast ease-out",
              "hover:border-foreground/20",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "active:scale-[0.96] active:cursor-grabbing"
            )}
          />
        ))}
      </SliderPrimitive.Control>
    </SliderPrimitive.Root>
  )
})
Slider.displayName = "Slider"

export { Slider }
