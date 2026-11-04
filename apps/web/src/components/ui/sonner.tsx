"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"

/*
 * Loam Sonner: the same floating surface, driven by the sonner queue.
 *
 * Sonner is styled through CSS variables, so every value here points at a
 * Loam token: the popover surface, the card radius and the floating shadow.
 */

/**
 * The custom properties sonner reads. CSS custom properties are valid style
 * values but absent from `React.CSSProperties`, so the surface names them.
 */
interface SonnerStyle extends React.CSSProperties {
  "--normal-bg": string
  "--normal-text": string
  "--normal-border": string
  "--border-radius": string
}

const SONNER_STYLE: SonnerStyle = {
  "--normal-bg": "var(--popover)",
  "--normal-text": "var(--popover-foreground)",
  "--normal-border": "var(--border)",
  "--border-radius": "var(--radius-card)",
}

/** The sonner toast stack, themed to the Loam floating surface. */
const Toaster = ({ ...props }: ToasterProps) => {
  const { resolvedTheme } = useTheme()
  const theme: ToasterProps["theme"] =
    resolvedTheme === "light" || resolvedTheme === "dark" ? resolvedTheme : "system"

  return (
    <Sonner
      theme={theme}
      className="toaster group"
      style={SONNER_STYLE}
      toastOptions={{
        classNames: {
          toast:
            "!bg-popover !text-popover-foreground !border !border-border !rounded-[var(--radius-card)] ![box-shadow:var(--shadow-lg)]",
          title: "!text-sm !font-semibold",
          description: "!text-sm !text-muted-foreground",
          actionButton:
            "!ml-3 !shrink-0 !self-center !rounded-[var(--radius-control)] !bg-primary !text-primary-foreground !text-xs !font-semibold",
          cancelButton:
            "!ml-2 !shrink-0 !self-center !rounded-[var(--radius-control)] !bg-secondary !text-secondary-foreground !text-xs !font-semibold",
          closeButton:
            "!rounded-[var(--radius-control)] !bg-popover !border-border !text-muted-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
