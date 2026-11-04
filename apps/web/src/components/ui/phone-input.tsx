import * as React from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { formFieldBase, formFieldSingleLine } from "./_shared"

/*
 * Loam PhoneInput: two field pills in a row, a dialling code and a number.
 * Both are single-line fields, so both wear the shared field recipe on the
 * control tier. Loam keeps them as two pills rather than one segmented box,
 * because a split pill would need a straight inner edge the system never uses.
 */

/** One dialling code offered by the PhoneInput. */
export interface PhoneCountry {
  /** Two-letter country code, used as the option value. */
  code: string
  /** The dialling prefix, for example `+44`. */
  dial: string
  label: string
}

/** The dialling codes the field offers when you pass none of your own. */
export const PHONE_COUNTRIES: PhoneCountry[] = [
  { code: "US", dial: "+1", label: "United States" },
  { code: "GB", dial: "+44", label: "United Kingdom" },
  { code: "DE", dial: "+49", label: "Germany" },
  { code: "FR", dial: "+33", label: "France" },
  { code: "JP", dial: "+81", label: "Japan" },
  { code: "AU", dial: "+61", label: "Australia" },
]

/** Phone field: a dialling-code pill beside the number pill. */
const PhoneInput = React.forwardRef<
  HTMLInputElement,
  Omit<React.ComponentProps<"input">, "type"> & {
    /** Dialling codes to offer. Defaults to `PHONE_COUNTRIES`. */
    countries?: PhoneCountry[]
    /** Country code selected at first render. */
    defaultCountry?: string
    /** Runs when the dialling code changes. */
    onCountryChange?: (code: string) => void
  }
>(
  (
    {
      className,
      countries = PHONE_COUNTRIES,
      defaultCountry,
      onCountryChange,
      disabled,
      placeholder = "(555) 000 0000",
      ...props
    },
    ref
  ) => {
    const [country, setCountry] = React.useState(
      defaultCountry ?? countries[0]?.code ?? ""
    )

    return (
      <div data-slot="phone-input" className="flex w-full items-center gap-2">
        <span className="relative shrink-0">
          <select
            data-slot="phone-input-country"
            value={country}
            disabled={disabled}
            aria-label="Country dialling code"
            onChange={event => {
              setCountry(event.target.value)
              onCountryChange?.(event.target.value)
            }}
            className={cn(
              formFieldBase,
              formFieldSingleLine,
              "w-auto cursor-pointer appearance-none bg-none pl-4 pr-9 font-semibold tabular-nums"
            )}
          >
            {countries.map(entry => (
              <option key={entry.code} value={entry.code}>
                {entry.dial} {entry.code}
              </option>
            ))}
          </select>
          <ChevronDown
            aria-hidden="true"
            className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
        </span>
        <input
          ref={ref}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          data-slot="phone-input-field"
          disabled={disabled}
          placeholder={placeholder}
          className={cn(formFieldBase, formFieldSingleLine, "flex-1 tabular-nums", className)}
          {...props}
        />
      </div>
    )
  }
)
PhoneInput.displayName = "PhoneInput"

export { PhoneInput }
