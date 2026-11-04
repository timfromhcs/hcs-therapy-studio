"use client"

import * as React from "react"
import { ChevronDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { floatingSurfaceBase, menuItemBase, pressSpring } from "./_shared"

/*
 * Loam MegaMenu: a pill bar that opens one wide floating panel.
 *
 * The bar and its triggers are controls, so they take the full pill radius.
 * The panel is a floating surface at the card radius (1.5rem) with the soft
 * large float, so it is the same paper as every menu and popover in Loam.
 */

/** One column of links inside an open panel. */
interface MegaMenuColumn {
  title: string
  items: string[]
}

/** One top-level entry in the bar and the columns it reveals. */
interface MegaMenuItem {
  id: string
  label: string
  columns: MegaMenuColumn[]
}

/** Props for the Loam mega menu. */
interface MegaMenuProps {
  items: MegaMenuItem[]
  className?: string
}

/** A wide navigation menu: pill triggers over one shared floating panel. */
export function MegaMenu({ items, className }: MegaMenuProps) {
  const [activeMenu, setActiveMenu] = React.useState<string | null>(null)
  const activeItem = items.find((item) => item.id === activeMenu)

  return (
    <div className={cn("flex w-full justify-center", className)}>
      <div
        className="relative w-full pb-2"
        onMouseLeave={() => setActiveMenu(null)}
      >
        <nav
          className={cn(
            "flex gap-1 p-1.5",
            "rounded-[var(--radius-control)] border border-border bg-card",
            "[box-shadow:var(--shadow-2xs)]"
          )}
        >
          {items.map((item) => {
            const isOpen = activeMenu === item.id
            return (
              <button
                key={item.id}
                type="button"
                aria-expanded={isOpen}
                onMouseEnter={() => setActiveMenu(item.id)}
                onFocus={() => setActiveMenu(item.id)}
                onClick={() => setActiveMenu(isOpen ? null : item.id)}
                className={cn(
                  "flex flex-1 select-none items-center justify-center gap-1.5",
                  "rounded-[var(--radius-control)] px-4 py-2.5",
                  "text-sm font-semibold cursor-pointer",
                  "transition-[transform,background-color,color] duration-fast ease-out",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isOpen
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  pressSpring
                )}
              >
                {item.label}
                <ChevronDown
                  aria-hidden="true"
                  className={cn(
                    "size-3 transition-transform duration-slow",
                    isOpen && "rotate-180"
                  )}
                />
              </button>
            )
          })}
        </nav>

        {activeItem && (
          <div
            data-slot="mega-menu-content"
            className={cn(
              floatingSurfaceBase,
              "absolute top-full left-0 right-0 z-50 mt-2 p-6",
              "animate-in fade-in-0 zoom-in-95 duration-fast"
            )}
          >
            <div className="flex flex-wrap gap-x-10 gap-y-6">
              {activeItem.columns.map((column) => (
                <div key={column.title} className="min-w-40 flex-1">
                  <div className="px-3 pb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                    {column.title}
                  </div>
                  <ul className="flex flex-col gap-0.5">
                    {column.items.map((link) => (
                      <li key={link}>
                        <a
                          href="#"
                          className={cn(
                            menuItemBase,
                            "cursor-pointer text-foreground",
                            "hover:bg-accent hover:text-accent-foreground",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                          )}
                        >
                          {link}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
