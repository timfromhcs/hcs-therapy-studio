import { useCallback, useEffect, useState } from "react"
import {
  BookOpen,
  Command,
  Cpu,
  Edit3,
  Home,
  MessageCircle,
  Moon,
  PlugZap,
  Settings,
  Shapes,
  Shield,
  Sun,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarItem,
} from "@/components/ui/sidebar"
import { StatusIndicator } from "@/components/ui/status-indicator"
import { api } from "@/lib/api"
import type { Locale, StringKey } from "@/lib/i18n"
import { t } from "@/lib/i18n"
import { ChatScreen } from "@/screens/chat"
import { HomeScreen } from "@/screens/home"
import { JournalScreen } from "@/screens/journal"
import { LabScreen } from "@/screens/lab"
import { ReflectionScreen } from "@/screens/reflection"
import { SafetyScreen } from "@/screens/safety"
import { SettingsScreen } from "@/screens/settings"
import { StudioScreen } from "@/screens/studio"

export type Screen =
  | "home"
  | "chat"
  | "journal"
  | "reflection"
  | "studio"
  | "lab"
  | "safety"
  | "settings"

type NavEntry = { screen: Screen; labelKey: StringKey; icon: React.ReactNode }

const NAV: { groupKey: StringKey; items: NavEntry[] }[] = [
  {
    groupKey: "navSession",
    items: [
      { screen: "home", labelKey: "navHome", icon: <Home /> },
      { screen: "chat", labelKey: "navChat", icon: <MessageCircle /> },
    ],
  },
  {
    groupKey: "navPrivate",
    items: [
      { screen: "journal", labelKey: "navJournal", icon: <BookOpen /> },
      { screen: "reflection", labelKey: "navReflection", icon: <Edit3 /> },
    ],
  },
  {
    groupKey: "navCreate",
    items: [{ screen: "studio", labelKey: "navStudio", icon: <Shapes /> }],
  },
  {
    groupKey: "navSystem",
    items: [
      { screen: "lab", labelKey: "navLab", icon: <Cpu /> },
      { screen: "safety", labelKey: "navSafety", icon: <Shield /> },
      { screen: "settings", labelKey: "navSettings", icon: <Settings /> },
    ],
  },
]

export function useHealth() {
  const [state, setState] = useState<{
    connected: boolean
    modelLoaded: boolean
    version: string | null
    checked: boolean
  }>({ connected: false, modelLoaded: false, version: null, checked: false })

  const refresh = useCallback(() => {
    api
      .health()
      .then((payload) =>
        setState({
          connected: payload.status === "ok",
          modelLoaded: payload.model_loaded,
          version: payload.version,
          checked: true,
        }),
      )
      .catch(() =>
        setState({ connected: false, modelLoaded: false, version: null, checked: true }),
      )
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 15000)
    return () => window.clearInterval(timer)
  }, [refresh])

  return { ...state, refresh }
}

export function AppShell({
  screen,
  onNavigate,
  locale,
  health,
}: {
  screen: Screen
  onNavigate: (screen: Screen) => void
  locale: Locale
  health: { connected: boolean; modelLoaded: boolean; version: string | null; checked: boolean }
}) {
  const [dark, setDark] = useState(
    () => document.documentElement.classList.contains("dark") || false,
  )
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [filter, setFilter] = useState("")

  // A page served from a public origin cannot reach 127.0.0.1: the browser
  // blocks it. Saying "start the studio and this page connects" would be a
  // promise the platform does not keep, so the hosted build says what is true.
  const hosted =
    typeof window !== "undefined" &&
    !/^(localhost|127\.0\.0\.1|\[::1\])$/.test(window.location.hostname)

  const toggleTheme = useCallback(() => {
    setDark((current) => {
      const next = !current
      document.documentElement.classList.toggle("dark", next)
      return next
    })
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setPaletteOpen((open) => !open)
        setFilter("")
        return
      }
      if (event.key === "Escape") setPaletteOpen(false)
      const target = event.target as HTMLElement | null
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return
      if (event.key === "d") toggleTheme()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [toggleTheme])

  const entries = NAV.flatMap((group) => group.items)
  const matches = entries.filter((item) =>
    t(locale, item.labelKey).toLowerCase().includes(filter.trim().toLowerCase()),
  )

  const go = (next: Screen) => {
    onNavigate(next)
    setPaletteOpen(false)
  }

  return (
    <div className="flex min-h-svh gap-4 bg-background p-4 text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-[var(--radius-control)] focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        {t(locale, "skipToContent")}
      </a>

      {paletteOpen && (
        <div
          className="fixed inset-0 z-40 flex items-start justify-center bg-foreground/40 p-4 pt-[12vh]"
          onClick={() => setPaletteOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t(locale, "paletteTitle")}
            className="w-full max-w-md rounded-[var(--radius-card)] border bg-background p-3 shadow-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <input
              autoFocus
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && matches[0]) go(matches[0].screen)
              }}
              placeholder={t(locale, "palettePlaceholder")}
              aria-label={t(locale, "palettePlaceholder")}
              className="mb-2 w-full rounded-[var(--radius-control)] border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            />
            <ul className="max-h-72 overflow-y-auto">
              {matches.map((item) => (
                <li key={item.screen}>
                  <button
                    type="button"
                    onClick={() => go(item.screen)}
                    className="flex w-full items-center gap-2 rounded-[var(--radius-control)] px-3 py-2 text-left text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50"
                  >
                    <span aria-hidden="true" className="[&_svg]:size-4">
                      {item.icon}
                    </span>
                    {t(locale, item.labelKey)}
                  </button>
                </li>
              ))}
              {matches.length === 0 && (
                <li className="px-3 py-2 text-sm text-muted-foreground">
                  {t(locale, "commonNone")}
                </li>
              )}
            </ul>
            <p className="mt-2 px-1 text-xs text-muted-foreground">{t(locale, "paletteHint")}</p>
          </div>
        </div>
      )}

      <div className="sticky top-4 hidden h-[calc(100svh-2rem)] md:block">
        <Sidebar className="h-full">
          <SidebarHeader>
            <span className="truncate">{t(locale, "productName")}</span>
          </SidebarHeader>
          <SidebarContent className="gap-5">
            {NAV.map((group) => (
              <SidebarGroup key={group.groupKey}>
                <SidebarGroupLabel>{t(locale, group.groupKey)}</SidebarGroupLabel>
                {group.items.map((item) => (
                  <SidebarItem
                    key={item.screen}
                    icon={item.icon}
                    active={screen === item.screen}
                    onClick={() => onNavigate(item.screen)}
                  >
                    {t(locale, item.labelKey)}
                  </SidebarItem>
                ))}
              </SidebarGroup>
            ))}
          </SidebarContent>
          <SidebarFooter className="gap-2">
            <StatusIndicator
              status={health.connected ? "online" : "error"}
              label={health.connected ? t(locale, "connected") : t(locale, "disconnected")}
            />
            <StatusIndicator
              status={health.modelLoaded ? "success" : "pending"}
              label={health.modelLoaded ? t(locale, "modelRunning") : t(locale, "modelStopped")}
            />
            <div className="flex items-center justify-between gap-2 px-1 pt-1">
              <span className="text-xs text-muted-foreground">
                {health.version ? `v${health.version}` : t(locale, "localOnly")}
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label={dark ? t(locale, "themeToLight") : t(locale, "themeToDark")}
              >
                {dark ? <Sun /> : <Moon />}
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="justify-start"
              onClick={() => {
                setFilter("")
                setPaletteOpen(true)
              }}
            >
              <Command />
              <span className="ml-1">Ctrl K</span>
            </Button>
          </SidebarFooter>
        </Sidebar>
      </div>

      <main id="main-content" className="min-w-0 flex-1 overflow-x-hidden pb-8">
        {health.checked && !health.connected && (
          <div
            role="status"
            className="mb-4 rounded-xl border border-[color:var(--border)] bg-[color:var(--muted)]/60 p-4"
          >
            <p className="flex items-center gap-2 text-sm font-medium">
              <PlugZap aria-hidden="true" className="size-4" />
              {t(locale, hosted ? "offlineHostedTitle" : "offlineTitle")}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {t(locale, hosted ? "offlineHostedBody" : "offlineBody")}
            </p>
            {!hosted && (
              <code className="mt-2 block overflow-x-auto rounded-md bg-[color:var(--card)] px-3 py-2 text-xs">
                hcs-therapy serve --port 8765 --start-backend
              </code>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
              {t(locale, hosted ? "offlineHostedNote" : "offlineNote")}
            </p>
          </div>
        )}
        <nav className="mb-4 flex gap-1 overflow-x-auto md:hidden" aria-label={t(locale, "navSession")}>
          {NAV.flatMap((group) => group.items).map((item) => (
            <Button
              key={item.screen}
              variant={screen === item.screen ? "default" : "ghost"}
              size="sm"
              onClick={() => onNavigate(item.screen)}
              aria-current={screen === item.screen ? "page" : undefined}
            >
              {t(locale, item.labelKey)}
            </Button>
          ))}
        </nav>
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
          <ScreenOutlet screen={screen} locale={locale} health={health} />
        </div>
      </main>
    </div>
  )
}

function ScreenOutlet({
  screen,
  locale,
  health,
}: {
  screen: Screen
  locale: Locale
  health: { connected: boolean; modelLoaded: boolean; version: string | null; checked: boolean }
}) {
  switch (screen) {
    case "home":
      return <HomeScreen locale={locale} health={health} />
    case "chat":
      return <ChatScreen locale={locale} health={health} />
    case "journal":
      return <JournalScreen locale={locale} />
    case "reflection":
      return <ReflectionScreen locale={locale} />
    case "studio":
      return <StudioScreen locale={locale} />
    case "lab":
      return <LabScreen locale={locale} />
    case "safety":
      return <SafetyScreen locale={locale} />
    case "settings":
      return <SettingsScreen locale={locale} />
    default:
      return <HomeScreen locale={locale} health={health} />
  }
}
