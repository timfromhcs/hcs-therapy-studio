import * as React from "react"

import { cn } from "@/lib/utils"
import { CopyButton } from "./copy-button"
import { pressSpring } from "./_shared"

/*
 * Loam CodeTabs: a card-tier muted surface with a rail of pills.
 *
 * The block takes the card radius (1.5rem) and clips its content. Each tab
 * trigger is a control-tier pill on that rail, and the active one takes the
 * flat primary fill, exactly as the primary Button does.
 */

/** One tab in the code block: its label, its language and its source. */
export interface CodeTabsItem {
  /** The label shown on the pill, usually a filename. */
  label: string
  /** Language name, used for the `language-` class on the code element. */
  lang: string
  /** The source text for this tab. */
  code: string
  /** Optional glyph shown before the label. */
  icon?: React.ReactNode
}

/** Props for the tabbed code surface. */
export interface CodeTabsProps extends React.ComponentProps<"div"> {
  /** The tabs to render, in rail order. */
  tabs: CodeTabsItem[]
  /** Index of the tab open on first paint. Defaults to 0. */
  defaultTab?: number
  /** Show a copy pill for the active tab. Defaults to true. */
  copyable?: boolean
  /** Extra actions on the rail, keyed off the active tab. */
  trailing?: (active: CodeTabsItem, index: number) => React.ReactNode
}

/** A tabbed code surface: pills on a rail, flat primary fill on the active one. */
function CodeTabs({
  tabs,
  defaultTab = 0,
  copyable = true,
  trailing,
  className,
  ...props
}: CodeTabsProps) {
  const [activeIndex, setActiveIndex] = React.useState(defaultTab)
  const active = tabs[activeIndex] ?? tabs[0]

  if (!active) return null

  return (
    <div
      data-slot="code-tabs"
      className={cn(
        "w-full overflow-hidden rounded-[var(--radius-card)] border border-border",
        "bg-muted font-mono",
        className
      )}
      {...props}
    >
      <div
        role="tablist"
        aria-label="Code examples"
        className="flex items-center gap-2 overflow-x-auto border-b border-border px-3 py-2"
      >
        {tabs.map((tab, index) => {
          const isActive = index === activeIndex
          return (
            <button
              key={tab.label}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveIndex(index)}
              className={cn(
                "inline-flex shrink-0 cursor-pointer items-center gap-1.5 whitespace-nowrap",
                "rounded-[var(--radius-control)] px-3.5 py-1.5",
                "font-sans text-xs font-semibold",
                "transition-[transform,background-color,color,box-shadow] duration-fast ease-out",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                pressSpring,
                isActive
                  ? "bg-primary text-primary-foreground [box-shadow:var(--shadow-xs)]"
                  : "bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          )
        })}

        {copyable || trailing ? (
          <div className="ml-auto flex shrink-0 items-center gap-2 pl-2">
            {trailing?.(active, activeIndex)}
            {copyable ? <CopyButton value={active.code} /> : null}
          </div>
        ) : null}
      </div>

      <div role="tabpanel" className="overflow-x-auto">
        <pre className="m-0 bg-transparent p-4 font-mono text-xs leading-relaxed text-foreground">
          <code className={`language-${active.lang}`}>{active.code}</code>
        </pre>
      </div>
    </div>
  )
}

export { CodeTabs }
