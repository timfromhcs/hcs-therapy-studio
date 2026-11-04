import { useCallback, useEffect, useState } from "react"
import {
  BookOpen,
  Cpu,
  Edit3,
  Home,
  MessageCircle,
  Moon,
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
  }>({ connected: false, modelLoaded: false, version: null })

  const refresh = useCallback(() => {
    api
      .health()
      .then((payload) =>
        setState({
          connected: payload.status === "ok",
          modelLoaded: payload.model_loaded,
          version: payload.version,
        }),
      )
      .catch(() => setState({ connected: false, modelLoaded: false, version: null }))
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
  health: { connected: boolean; modelLoaded: boolean; version: string | null }
}) {
  const [dark, setDark] = useState(
    () => document.documentElement.classList.contains("dark") || false,
  )

  const toggleTheme = () => {
    const next = !dark
    setDark(next)
    document.documentElement.classList.toggle("dark", next)
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return
      if (event.key === "d") toggleTheme()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  })

  return (
    <div className="flex min-h-svh gap-4 bg-background p-4 text-foreground">
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
                aria-label={dark ? t(locale, "navSettings") : t(locale, "navSettings")}
              >
                {dark ? <Sun /> : <Moon />}
              </Button>
            </div>
          </SidebarFooter>
        </Sidebar>
      </div>

      <main className="min-w-0 flex-1 overflow-x-hidden pb-8">
        <nav className="mb-4 flex gap-1 overflow-x-auto md:hidden" aria-label="Navigation">
          {NAV.flatMap((group) => group.items).map((item) => (
            <Button
              key={item.screen}
              variant={screen === item.screen ? "default" : "ghost"}
              size="sm"
              onClick={() => onNavigate(item.screen)}
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
  health: { connected: boolean; modelLoaded: boolean; version: string | null }
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
